use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::Arc;
use crate::config::AuthConfig;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    pub sub: Option<String>,
    pub exp: Option<usize>,
    pub iss: Option<String>,
    pub aud: Option<serde_json::Value>,
    pub name: Option<String>,
    pub preferred_username: Option<String>,
    pub email: Option<String>,
}

#[derive(Clone, Debug)]
pub struct AuthenticatedUser {
    pub user_id: String,
    pub user_name: String,
}

pub async fn auth_middleware(
    request: Request,
    next: Next,
) -> Response {
    let path = request.uri().path();

    // Health checks remain public without authentication
    if path == "/health" || path.ends_with("/health") {
        return next.run(request).await;
    }

    // Options CORS preflight requests bypass auth
    if request.method() == axum::http::Method::OPTIONS {
        return next.run(request).await;
    }

    let auth_config = request.extensions().get::<Arc<Option<AuthConfig>>>().cloned();

    let auth_header = match request.headers().get("Authorization").and_then(|h| h.to_str().ok()) {
        Some(h) if h.to_lowercase().starts_with("bearer ") => &h[7..].trim(),
        _ => {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({ "error": "Bearer token required" })),
            )
                .into_response();
        }
    };

    if auth_header.is_empty() {
        return (
            StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Bearer token required" })),
        )
            .into_response();
    }

    let token = *auth_header;

    // If AuthConfig is present and configured, validate RS256 JWT
    if let Some(arc_cfg) = auth_config {
        if let Some(ref cfg) = *arc_cfg {
            let pem = cfg.jwt_public_key.replace("\\n", "\n");
            let decoding_key = match DecodingKey::from_rsa_pem(pem.as_bytes()) {
                Ok(k) => k,
                Err(e) => {
                    tracing::error!("Invalid JWT public key PEM: {e}");
                    return (
                        StatusCode::SERVICE_UNAVAILABLE,
                        Json(json!({ "error": "Authentication is not configured" })),
                    )
                        .into_response();
                }
            };

            let mut validation = Validation::new(Algorithm::RS256);
            validation.set_issuer(&[&cfg.jwt_issuer]);
            validation.set_audience(&[&cfg.jwt_audience]);
            validation.validate_exp = true;
            validation.set_required_spec_claims(&["exp", "iss", "aud", "sub"]);

            let token_data = match decode::<Claims>(token, &decoding_key, &validation) {
                Ok(d) => d,
                Err(e) => {
                    tracing::warn!("JWT decode error: {e}");
                    return (
                        StatusCode::UNAUTHORIZED,
                        Json(json!({ "error": "Invalid bearer token" })),
                    )
                        .into_response();
                }
            };

            let sub = match token_data.claims.sub {
                Some(ref s) if !s.trim().is_empty() => s.clone(),
                _ => {
                    return (
                        StatusCode::UNAUTHORIZED,
                        Json(json!({ "error": "Bearer token has no user identity claim" })),
                    )
                        .into_response();
                }
            };

            let user_name = token_data
                .claims
                .name
                .or(token_data.claims.preferred_username)
                .or(token_data.claims.email)
                .unwrap_or_else(|| sub.clone());

            let mut request = request;
            request.extensions_mut().insert(AuthenticatedUser {
                user_id: sub,
                user_name,
            });

            return next.run(request).await;
        }
    }

    // In dev / test when auth config is omitted, attempt insecure parse for sub claim
    // But fail closed if token is invalid
    return (
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({ "error": "Authentication is not configured" })),
    )
        .into_response();
}
