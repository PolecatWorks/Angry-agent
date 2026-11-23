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

#[derive(Debug, Error)]
pub enum SessionError {
    #[error("No active form registered for this thread")]
    NoActiveForm,

    #[error("Failed to apply patch: {0}")]
    Patch(#[from] json_patch::PatchError),
}

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("Invalid JSON payload: {0}")]
    Json(#[from] serde_json::Error),

    #[error("JSON Patch error: {0}")]
    Patch(#[from] json_patch::PatchError),

    #[error(transparent)]
    Session(#[from] SessionError),

    #[error("{0}")]
    NotFound(String),

    #[error("{0}")]
    Forbidden(String),

    #[error("{0}")]
    BadRequest(String),

    #[error("{0}")]
    Conflict(String),
}

impl axum::response::IntoResponse for ApiError {
    fn into_response(self) -> axum::response::Response {
        use axum::http::StatusCode;
        use axum::Json;
        use serde_json::json;

        let (status, message) = match &self {
            ApiError::Database(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()),
            ApiError::Json(e) => (StatusCode::BAD_REQUEST, format!("Invalid JSON patch: {e}")),
            ApiError::Patch(e) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                format!("Failed to apply JSON patch: {e}"),
            ),
            ApiError::Session(SessionError::NoActiveForm) => {
                (StatusCode::BAD_REQUEST, self.to_string())
            }
            ApiError::Session(SessionError::Patch(_)) => {
                (StatusCode::UNPROCESSABLE_ENTITY, self.to_string())
            }
            ApiError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            ApiError::Forbidden(msg) => (StatusCode::FORBIDDEN, msg.clone()),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            ApiError::Conflict(msg) => (StatusCode::CONFLICT, msg.clone()),
        };

        (status, Json(json!({ "error": message }))).into_response()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum::response::IntoResponse;

    #[test]
    fn api_error_maps_variants_to_expected_http_status_codes() {
        assert_eq!(
            ApiError::NotFound("Missing item".into())
                .into_response()
                .status(),
            StatusCode::NOT_FOUND
        );
        assert_eq!(
            ApiError::Forbidden("Denied".into())
                .into_response()
                .status(),
            StatusCode::FORBIDDEN
        );
        assert_eq!(
            ApiError::BadRequest("Invalid field".into())
                .into_response()
                .status(),
            StatusCode::BAD_REQUEST
        );
        assert_eq!(
            ApiError::Conflict("Busy".into()).into_response().status(),
            StatusCode::CONFLICT
        );
        assert_eq!(
            ApiError::Session(SessionError::NoActiveForm)
                .into_response()
                .status(),
            StatusCode::BAD_REQUEST
        );
        assert_eq!(
            ApiError::Database(sqlx::Error::RowNotFound)
                .into_response()
                .status(),
            StatusCode::INTERNAL_SERVER_ERROR
        );

        let bad_json_err = serde_json::from_str::<serde_json::Value>("{invalid").unwrap_err();
        assert_eq!(
            ApiError::from(bad_json_err).into_response().status(),
            StatusCode::BAD_REQUEST
        );

        let mut doc = serde_json::json!({ "a": 1 });
        let bad_patch: json_patch::Patch = serde_json::from_value(serde_json::json!([
            { "op": "replace", "path": "/nonexistent", "value": 2 }
        ]))
        .unwrap();
        let patch_err = json_patch::patch(&mut doc, &bad_patch).unwrap_err();
        assert_eq!(
            ApiError::from(patch_err).into_response().status(),
            StatusCode::UNPROCESSABLE_ENTITY
        );
    }
}
