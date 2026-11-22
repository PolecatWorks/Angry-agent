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
