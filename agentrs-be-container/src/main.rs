use agentrs_be::api::{create_prefixed_router, AppState};
use agentrs_be::auth::auth_middleware;
use agentrs_be::config::ServiceConfig;
use agentrs_be::hams::init_hams;
use agentrs_be::migrations::run_migrations;
use agentrs_be::session_store::SessionStore;
use clap::{Parser, Subcommand, ValueEnum};
use sqlx::postgres::PgPoolOptions;
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::{error, info, warn};

#[derive(Parser, Debug)]
#[command(
    name = "agentrs-be",
    version,
    about = "Angry Agent Rust Backend Service"
)]
struct Cli {
    #[arg(long, default_value = "false")]
    debug: bool,

    #[command(subcommand)]
    command: Option<Commands>,

    /// Fallback option for running directly with --config
    #[arg(long)]
    config: Option<PathBuf>,

    /// Fallback option for running directly with --secrets
    #[arg(long)]
    secrets: Option<PathBuf>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Start the web server and background services
    Start {
        #[arg(long)]
        config: Option<PathBuf>,
        #[arg(long)]
        secrets: Option<PathBuf>,
    },
    /// Run database schema migrations
    Migrate {
        #[arg(long, value_enum, default_value_t = MigrationAction::Apply)]
        action: MigrationAction,
        #[arg(long)]
        config: Option<PathBuf>,
        #[arg(long)]
        secrets: Option<PathBuf>,
    },
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum MigrationAction {
    Apply,
    Rollback,
    List,
}

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,tower_http=debug".into()),
        )
        .init();

    let cli = Cli::parse();

    match cli.command {
        Some(Commands::Migrate {
            action,
            config,
            secrets,
        }) => {
            let rt = tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .build()
                .expect("Failed to create Tokio runtime");
            rt.block_on(async {
                run_migrate_cmd(action, config.as_deref(), secrets.as_deref()).await;
            });
        }
        Some(Commands::Start { config, secrets }) => {
            run_start_cmd(config.as_deref(), secrets.as_deref());
        }
        None => {
            // If invoked without a subcommand, check if --config was supplied or run default start
            run_start_cmd(cli.config.as_deref(), cli.secrets.as_deref());
        }
    }
}

fn load_service_config(config_path: Option<&Path>, secrets_path: Option<&Path>) -> ServiceConfig {
    if let Some(cfg_p) = config_path {
        if cfg_p.exists() {
            info!("Loading configuration from {}", cfg_p.display());
            match ServiceConfig::from_yaml_and_secrets(cfg_p, secrets_path) {
                Ok(cfg) => return cfg,
                Err(e) => {
                    warn!(
                        "Failed to load configuration from {}: {e}. Falling back to defaults.",
                        cfg_p.display()
                    );
                }
            }
        } else {
            warn!(
                "Config file {} not found; falling back to defaults.",
                cfg_p.display()
            );
        }
    }

    // Default configuration
    ServiceConfig {
        webservice: Default::default(),
        auth: None,
        persistence: None,
        hams: None,
    }
}

async fn create_pg_pool_from_config(config: &ServiceConfig) -> Option<sqlx::PgPool> {
    let dsn = config
        .persistence
        .as_ref()
        .and_then(|p| p.db.as_ref())
        .and_then(|db| db.connection.as_ref())
        .and_then(|conn| conn.dsn())
        .or_else(|| std::env::var("DATABASE_URL").ok());

    let Some(dsn_str) = dsn else {
        warn!("No database connection URL or DSN configured. Running without database pool.");
        return None;
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

    match PgPoolOptions::new()
        .max_connections(pool_size)
        .acquire_timeout(Duration::from_secs(acquire_timeout))
        .connect(&dsn_str)
        .await
    {
        Ok(pool) => {
            info!("Connected to PostgreSQL database successfully");
            Some(pool)
        }
        Err(e) => {
            error!("Failed to connect to PostgreSQL database: {e}");
            None
        }
    }
}

async fn run_migrate_cmd(action: MigrationAction, config: Option<&Path>, secrets: Option<&Path>) {
    info!("Running migrate command with action: {:?}", action);
    let cfg = load_service_config(config, secrets);

    let pool = create_pg_pool_from_config(&cfg)
        .await
        .expect("Database connection is required for migrations");

    match action {
        MigrationAction::Apply => {
            if let Err(e) = run_migrations(&pool).await {
                error!("Migration failed: {e}");
                std::process::exit(1);
            }
            info!("Migrations applied successfully.");
        }
        MigrationAction::List => {
            info!("Migration action list completed.");
        }
        MigrationAction::Rollback => {
            warn!("Rollback is not currently implemented in agentrs-be; skipping.");
        }
    }
}

fn run_start_cmd(config_path: Option<&Path>, secrets_path: Option<&Path>) {
    let cfg = load_service_config(config_path, secrets_path);

    // Resolve port from env var or webservice config
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .or_else(|| {
            cfg.webservice
                .url
                .split(':')
                .next_back()
                .and_then(|p| p.parse().ok())
        })
        .unwrap_or(8080);

    // Resolve HAMS port from env var or hams config
    let hams_port: u16 = std::env::var("HAMS_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .or_else(|| cfg.hams.as_ref().and_then(|h| h.port))
        .unwrap_or(8079);

    // Initialize and start HaMS health and monitoring before entering Tokio runtime
    let mut hams = init_hams(hams_port).expect("Failed to initialize HaMS");
    if let Err(e) = hams.start() {
        error!("Failed to start HaMS: {e}");
    } else {
        info!("HaMS health service running on port {hams_port} (/hams/alive, /hams/ready, /hams/startup)");
    }

    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime");

    rt.block_on(async {
        let store = SessionStore::new();
        let catalog = agentrs_be::catalog::FormCatalog::new();
        let pool = create_pg_pool_from_config(&cfg).await;

        // Automigrate if configured
        if let Some(ref p) = pool {
            let automigrate = cfg
                .persistence
                .as_ref()
                .and_then(|persist| persist.db.as_ref())
                .and_then(|db| db.automigrate)
                .unwrap_or(false);

            if automigrate {
                info!("Automigrate is enabled. Running migrations...");
                if let Err(e) = run_migrations(p).await {
                    error!("Automigrate failed: {e}");
                }
            }
        }

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

        // Create router with prefix and auth middleware
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

        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        info!("🚀 agentrs-be-container starting on http://{}", addr);

        let listener = match tokio::net::TcpListener::bind(addr).await {
            Ok(l) => l,
            Err(e) => {
                error!("Failed to bind TCP listener on {}: {e}", addr);
                return;
            }
        };

        if let Err(e) = axum::serve(listener, app).await {
            error!("Server error: {e}");
        }
    });

    if let Err(e) = hams.stop() {
        info!("HaMS stopped or already stopped: {e}");
    }
}
