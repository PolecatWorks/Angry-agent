use agentrs_be::api::{create_router, AppState};
use agentrs_be::hams::init_hams;
use agentrs_be::session_store::SessionStore;
use std::net::SocketAddr;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::{error, info};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,tower_http=debug".into()),
        )
        .init();

    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8081);

    let hams_port: u16 = std::env::var("HAMS_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8078);

    // Initialize and start HaMS health and monitoring
    let mut hams = init_hams(hams_port).expect("Failed to initialize HaMS");
    if let Err(e) = hams.start() {
        error!("Failed to start HaMS: {e}");
    } else {
        info!("HaMS health service running on port {hams_port} (/hams/alive, /hams/ready, /hams/startup)");
    }

    let store = SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = AppState { store, catalog };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = create_router(state)
        .layer(cors)
        .layer(TraceLayer::new_for_http());

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    info!("🚀 agentrs-be-container starting on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("Failed to bind TCP listener");

    if let Err(e) = axum::serve(listener, app).await {
        error!("Server error: {e}");
    }

    if let Err(e) = hams.stop() {
        info!("HaMS stopped or already stopped: {e}");
    }
}
