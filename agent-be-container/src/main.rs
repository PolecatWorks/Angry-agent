use agentrs_be::api::{create_prefixed_router, AppState};
use agentrs_be::auth::auth_middleware;
use agentrs_be::cli::{Cli, Commands, MigrationAction};
use agentrs_be::config::ServiceConfig;
use agentrs_be::error::{BootError, ConfigError};
use agentrs_be::hams::init_hams;
use agentrs_be::migrations::{rollback_migrations, run_migrations, MIGRATOR};
use agentrs_be::session_store::SessionStore;
use clap::Parser;
use sqlx::postgres::PgPoolOptions;
use std::net::SocketAddr;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::{error, info, warn};

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,tower_http=debug".into()),
        )
        .init();

    let cli = Cli::parse();

    let result = match cli.command {
        Commands::Migrate {
            action,
            config,
            secrets,
        } => tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(BootError::Runtime)
            .and_then(|rt| rt.block_on(run_migrate_cmd(action, &config, secrets.as_deref()))),
        Commands::Start { config, secrets } => run_start_cmd(&config, secrets.as_deref()),
    };

    if let Err(err) = result {
        error!("Fatal error: {err}");
        std::process::exit(1);
    }
}

fn load_service_config(
    config_path: &Path,
    secrets_path: Option<&Path>,
) -> Result<ServiceConfig, ConfigError> {
    info!("Loading configuration from {}", config_path.display());
    ServiceConfig::from_yaml_and_secrets(config_path, secrets_path)
}

async fn create_pg_pool_from_config(
    config: &ServiceConfig,
) -> Result<Option<sqlx::PgPool>, BootError> {
    let dsn = config
        .persistence
        .as_ref()
        .and_then(|p| p.db.as_ref())
        .and_then(|db| db.connection.as_ref())
        .and_then(|conn| conn.dsn());

    let Some(dsn_str) = dsn else {
        warn!("No database connection URL or DSN configured. Running without database pool.");
        return Ok(None);
    };

    info!("Connecting to PostgreSQL database...");
    let pool_size = config
        .persistence
        .as_ref()
        .and_then(|p| p.db.as_ref())
        .and_then(|db| db.pool_size)
        .unwrap_or(10);

    let acquire_timeout = config
        .persistence
        .as_ref()
        .and_then(|p| p.db.as_ref())
        .and_then(|db| db.acquire_timeout)
        .unwrap_or(5);

    let pool = PgPoolOptions::new()
        .max_connections(pool_size)
        .acquire_timeout(Duration::from_secs(acquire_timeout))
        .connect(&dsn_str)
        .await
        .map_err(BootError::DatabaseConnect)?;

    info!("Connected to PostgreSQL database successfully");
    Ok(Some(pool))
}

async fn run_migrate_cmd(
    action: MigrationAction,
    config: &Path,
    secrets: Option<&Path>,
) -> Result<(), BootError> {
    info!("Running migrate command with action: {:?}", action);
    let cfg = load_service_config(config, secrets)?;

    match action {
        MigrationAction::List => {
            for m in MIGRATOR.iter() {
                info!(
                    "Migration {}: {} ({:?})",
                    m.version, m.description, m.migration_type
                );
            }
            info!("Migration action list completed.");
        }
        MigrationAction::Apply => {
            let pool = create_pg_pool_from_config(&cfg)
                .await?
                .ok_or(BootError::DatabaseMissing)?;
            run_migrations(&pool).await?;
            info!("Migrations applied successfully.");
        }
        MigrationAction::Rollback => {
            let pool = create_pg_pool_from_config(&cfg)
                .await?
                .ok_or(BootError::DatabaseMissing)?;
            rollback_migrations(&pool).await?;
            info!("Migrations rolled back successfully.");
        }
    }

    Ok(())
}

fn run_start_cmd(config_path: &Path, secrets_path: Option<&Path>) -> Result<(), BootError> {
    // 1. Load & validate configuration
    let cfg = load_service_config(config_path, secrets_path)?;

    // Resolve port from validated webservice config
    let port: u16 = cfg.webservice.port()?;

    // Resolve HAMS port from hams config
    let hams_port: u16 = cfg.hams.as_ref().and_then(|h| h.port).unwrap_or(8079);

    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .map_err(BootError::Runtime)?;

    let (listener, app, addr) = rt.block_on(async {
        // 2. Connect PgPool (fatal if DB URL configured and connect fails)
        let pool = create_pg_pool_from_config(&cfg).await?;

        // 3. Run migrations (fatal on error)
        if let Some(ref p) = pool {
            let automigrate = cfg
                .persistence
                .as_ref()
                .and_then(|persist| persist.db.as_ref())
                .and_then(|db| db.automigrate)
                .unwrap_or(false);

            if automigrate {
                info!("Automigrate is enabled. Running migrations...");
                run_migrations(p).await?;
            }
        }

        // 4. Init stores, catalog, and router
        let store = SessionStore::new();
        let catalog = agentrs_be::catalog::FormCatalog::new();
        let state = AppState {
            store,
            catalog,
            pool,
        };

        let cors = CorsLayer::new()
            .allow_origin(Any)
            .allow_methods(Any)
            .allow_headers(Any);

        let auth_config_arc = Arc::new(cfg.auth.clone());

        let prefix = &cfg.webservice.prefix;
        let mut app = create_prefixed_router(state, prefix)
            .layer(cors)
            .layer(TraceLayer::new_for_http());

        // Attach auth middleware if auth is configured
        if cfg.auth.is_some() {
            app = app
                .layer(axum::middleware::from_fn(auth_middleware))
                .layer(axum::Extension(auth_config_arc));
        }

        // 5. Bind TcpListener before starting HaMS or marking ready
        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        let listener = tokio::net::TcpListener::bind(addr)
            .await
            .map_err(|source| BootError::Bind { addr, source })?;

        Ok::<_, BootError>((listener, app, addr))
    })?;

    // 6. Start HaMS & flip ready probe outside Tokio runtime (hams uses internal block_on)
    // only after all boot checks, migrations, and TCP bind succeed.
    let mut hams = init_hams(hams_port)?;
    hams.start()?;
    hams.mark_ready();
    info!(
        "HaMS health service running on port {hams_port} (/hams/alive, /hams/ready, /hams/startup)"
    );

    // 7. Serve HTTP traffic
    info!("🚀 agentrs-be-container starting on http://{}", addr);
    let serve_result =
        rt.block_on(async { axum::serve(listener, app).await.map_err(BootError::Serve) });

    hams.mark_not_ready();
    if let Err(e) = hams.stop() {
        info!("HaMS stopped or already stopped: {e}");
    }

    serve_result
}
