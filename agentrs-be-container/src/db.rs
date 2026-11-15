use sqlx::postgres::{PgPool, PgPoolOptions};
use std::env;
use std::time::Duration;
use tracing::info;

pub async fn create_pool() -> Result<PgPool, sqlx::Error> {
    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| {
        "postgres://postgres:mysecretpassword@localhost:5432/agentdb".to_string()
    });

    info!("Connecting to PostgreSQL database...");
    let pool = PgPoolOptions::new()
        .max_connections(10)
        .acquire_timeout(Duration::from_secs(5))
        .connect(&database_url)
        .await?;

    info!("Connected to PostgreSQL database successfully");
    Ok(pool)
}
