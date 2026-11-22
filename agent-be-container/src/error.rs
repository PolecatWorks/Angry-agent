use std::path::PathBuf;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("Failed to read configuration file {path}: {source}")]
    ReadFile {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },

    #[error("Failed to parse YAML configuration {path}: {source}")]
    ParseYaml {
        path: PathBuf,
        #[source]
        source: serde_yaml::Error,
    },

    #[error("Failed to read secret file {path}: {source}")]
    ReadSecret {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },

    #[error("Secrets directory does not exist or is not a directory: {path}")]
    InvalidSecretsDir { path: PathBuf },

    #[error("Invalid webservice URL: {0}")]
    InvalidWebServerUrl(String),

    #[error("Invalid webservice port in URL: {0}")]
    InvalidWebServerPort(String),

    #[error("Invalid webservice prefix: {0}")]
    InvalidWebServerPrefix(String),

    #[error("Invalid auth configuration: {0}")]
    InvalidAuthConfig(String),

    #[error("Invalid database configuration: {0}")]
    InvalidDbConfig(String),

    #[error("Invalid HaMS configuration: {0}")]
    InvalidHamsConfig(String),
}

#[derive(Debug, Error)]
pub enum BootError {
    #[error(transparent)]
    Config(#[from] ConfigError),

    #[error("Database connection URL or DSN is required for migrations")]
    DatabaseMissing,

    #[error("Failed to connect to PostgreSQL database: {0}")]
    DatabaseConnect(#[source] sqlx::Error),

    #[error("Database migration failed: {0}")]
    Migration(#[from] sqlx::migrate::MigrateError),

    #[error("Failed to create Tokio runtime: {0}")]
    Runtime(#[source] std::io::Error),

    #[error("HaMS error: {0}")]
    Hams(#[from] hams::error::HamsError),

    #[error("Failed to bind TCP listener on {addr}: {source}")]
    Bind {
        addr: std::net::SocketAddr,
        #[source]
        source: std::io::Error,
    },

    #[error("HTTP server error: {0}")]
    Serve(#[source] std::io::Error),
}
