use sqlx::PgPool;
use tracing::info;

pub async fn run_migrations(pool: &PgPool) -> Result<(), sqlx::Error> {
    info!("Running database schema migrations for agentrs-be...");

    // 001_initial_schema
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            color TEXT,
            status_msg TEXT,
            status_updated_at TIMESTAMP WITH TIME ZONE,
            locked_until TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
        "#,
    )
    .execute(pool)
    .await?;

    // 002_thread_access
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS thread_access (
            thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL,
            access_level TEXT DEFAULT 'read',
            granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (thread_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_thread_access_user_id ON thread_access(user_id);
        "#,
    )
    .execute(pool)
    .await?;

    // 003_users_table
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT,
            first_login_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_login_at TIMESTAMP WITH TIME ZONE
        );
        "#,
    )
    .execute(pool)
    .await?;

    // 004_visualizations
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS visualizations (
            id UUID PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
            mfe VARCHAR(255) NOT NULL,
            component VARCHAR(255) NOT NULL,
            content JSONB NOT NULL,
            description TEXT,
            order_index INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_visualizations_thread_id ON visualizations(thread_id);
        "#,
    )
    .execute(pool)
    .await?;

    // 005_agent_definitions
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS agent_definitions (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        "#,
    )
    .execute(pool)
    .await?;

    // 008_learning_mode
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            learning_mode_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        "#,
    )
    .execute(pool)
    .await?;

    info!("Database schema migrations applied successfully.");
    Ok(())
}
