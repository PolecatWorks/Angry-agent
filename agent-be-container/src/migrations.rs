use sqlx::migrate::Migrator;
use sqlx::PgPool;
use tracing::info;

pub static MIGRATOR: Migrator = sqlx::migrate!("./migrations");

pub async fn run_migrations(pool: &PgPool) -> Result<(), sqlx::migrate::MigrateError> {
    info!("Running database schema migrations for agentrs-be...");
    MIGRATOR.run(pool).await?;
    info!("Database schema migrations applied successfully.");
    Ok(())
}

pub async fn rollback_migrations(pool: &PgPool) -> Result<(), sqlx::migrate::MigrateError> {
    info!("Rolling back database schema migrations for agentrs-be...");
    MIGRATOR.undo(pool, 0).await?;
    info!("Database schema migrations rolled back successfully.");
    Ok(())
}
