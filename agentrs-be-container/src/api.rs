use crate::broadcaster::EventBroadcaster;
use crate::catalog::FormCatalog;
use crate::models::{AgUiEvent, FormSyncRequest, RegisterFormRequest, RunAgentRequest};
use crate::session_store::SessionStore;
use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::sse::{Event, KeepAlive, Sse},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use futures::stream::Stream;
use serde::{Deserialize, Serialize};
use serde_json::json;
use sqlx::PgPool;
use std::convert::Infallible;
use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tokio_stream::StreamExt;
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    pub store: SessionStore,
    pub catalog: FormCatalog,
    pub pool: Option<PgPool>,
}

pub fn create_router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health_handler))
        .route("/api/user/settings", get(get_user_settings_handler).put(update_user_settings_handler))
        .route("/api/forms", get(list_forms_handler))
        .route("/api/forms/{form_id}", get(get_form_handler))
        .route("/api/threads", get(list_threads_handler))
        .route(
            "/api/threads/{thread_id}",
            get(get_thread_handler)
                .put(update_thread_handler)
                .delete(delete_thread_handler),
        )
        .route("/api/form/register", post(register_form_handler))
        .route("/api/form/sync", post(sync_form_handler))
        .route("/api/agent/run", post(run_agent_handler))
        .with_state(state)
}

fn extract_user_id(headers: &HeaderMap) -> String {
    headers
        .get("X-User-ID")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("default_user")
        .to_string()
}

#[derive(Debug, Deserialize, Serialize)]
pub struct UserSettingsResponse {
    pub learning_mode_enabled: bool,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct UpdateUserSettingsRequest {
    pub learning_mode_enabled: bool,
}

pub async fn get_user_settings_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    let Some(pool) = &state.pool else {
        return Ok(Json(json!({ "learning_mode_enabled": false })));
    };

    let row = sqlx::query_as::<_, (Option<bool>,)>(
        "SELECT learning_mode_enabled FROM users WHERE user_id = $1",
    )
    .bind(user_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    let learning_mode_enabled = row.and_then(|(val,)| val).unwrap_or(false);

    Ok(Json(json!({ "learning_mode_enabled": learning_mode_enabled })))
}

pub async fn update_user_settings_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<UpdateUserSettingsRequest>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    let Some(pool) = &state.pool else {
        return Ok(Json(json!({ "status": "updated" })));
    };

    sqlx::query(
        r#"
        INSERT INTO users (user_id, learning_mode_enabled)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE
        SET learning_mode_enabled = EXCLUDED.learning_mode_enabled
        "#,
    )
    .bind(user_id)
    .bind(payload.learning_mode_enabled)
    .execute(pool)
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    Ok(Json(json!({ "status": "updated" })))
}

async fn health_handler() -> impl IntoResponse {
    Json(json!({
        "status": "ok",
        "container": "agentrs-be-container",
        "protocol": "AG-UI v1.0",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

async fn list_forms_handler(State(state): State<AppState>) -> impl IntoResponse {
    let forms = state.catalog.list();
    Json(json!({ "forms": forms }))
}

async fn get_form_handler(
    State(state): State<AppState>,
    Path(form_id): Path<String>,
) -> impl IntoResponse {
    match state.catalog.get(&form_id) {
        Some(form) => Json(json!({ "form": form })),
        None => Json(json!({ "error": "Form not found" })),
    }
}

#[derive(Debug, Deserialize, Serialize)]
pub struct UpdateThreadRequest {
    pub color: String,
    pub title: String,
    pub learning_mode_enabled: Option<bool>,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct ThreadSummary {
    pub thread_id: String,
    pub title: Option<String>,
    pub color: Option<String>,
    pub created_at: Option<chrono::DateTime<chrono::Utc>>,
}

async fn list_threads_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    if let Some(pool) = &state.pool {
        // Track user login
        let _ = sqlx::query(
            r#"
            INSERT INTO users (user_id, user_name, last_login_at)
            VALUES ($1, $1, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET user_name = EXCLUDED.user_name,
                last_login_at = NOW()
            "#,
        )
        .bind(&user_id)
        .execute(pool)
        .await;

        let rows = sqlx::query_as::<_, ThreadSummary>(
            r#"
            SELECT DISTINCT t.thread_id, t.title, t.color, t.created_at
            FROM threads t
            LEFT JOIN thread_access ta ON t.thread_id = ta.thread_id
            WHERE t.user_id = $1 OR ta.user_id = $1
            ORDER BY t.created_at DESC
            "#,
        )
        .bind(&user_id)
        .fetch_all(pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({ "error": e.to_string() })),
            )
        })?;

        let threads_json: Vec<serde_json::Value> = rows
            .into_iter()
            .map(|t| {
                json!({
                    "thread_id": t.thread_id,
                    "title": t.title,
                    "color": t.color,
                    "created_at": t.created_at.map(|c| c.to_rfc3339()),
                })
            })
            .collect();

        return Ok(Json(json!({ "threads": threads_json })));
    }

    let threads = state.store.list_user_sessions(&user_id);
    Ok(Json(json!({ "threads": threads })))
}

async fn update_thread_handler(
    State(state): State<AppState>,
    Path(thread_id): Path<String>,
    headers: HeaderMap,
    Json(payload): Json<UpdateThreadRequest>,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    if let Some(pool) = &state.pool {
        let result = sqlx::query(
            r#"
            UPDATE threads
            SET color = $1, title = $2, updated_at = NOW()
            WHERE thread_id = $3 AND user_id = $4
            "#,
        )
        .bind(&payload.color)
        .bind(&payload.title)
        .bind(&thread_id)
        .bind(&user_id)
        .execute(pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({ "error": e.to_string() })),
            )
        })?;

        if result.rows_affected() == 0 {
            return Err((
                StatusCode::NOT_FOUND,
                Json(json!({ "error": "Not found or access denied" })),
            ));
        }

        return Ok(Json(json!({ "status": "updated" })));
    }

    // Fallback in-memory
    match state.store.get(&thread_id) {
        Some(_) => Ok(Json(json!({ "status": "updated" }))),
        None => Err((
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "Not found or access denied" })),
        )),
    }
}

async fn delete_thread_handler(
    State(state): State<AppState>,
    Path(thread_id): Path<String>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    if let Some(pool) = &state.pool {
        let result = sqlx::query(
            "DELETE FROM threads WHERE thread_id = $1 AND user_id = $2",
        )
        .bind(&thread_id)
        .bind(&user_id)
        .execute(pool)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({ "error": e.to_string() })),
            )
        })?;

        if result.rows_affected() == 0 {
            return Err((
                StatusCode::NOT_FOUND,
                Json(json!({ "error": "Not found or access denied" })),
            ));
        }

        return Ok(Json(json!({ "status": "deleted" })));
    }

    // Fallback in-memory
    state.store.remove(&thread_id);
    Ok(Json(json!({ "status": "deleted" })))
}

async fn get_thread_handler(
    State(state): State<AppState>,
    Path(thread_id): Path<String>,
) -> impl IntoResponse {
    match state.store.get(&thread_id) {
        Some(session) => Json(json!({ "session": session })),
        None => Json(json!({ "error": "Thread not found" })),
    }
}

async fn register_form_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<RegisterFormRequest>,
) -> impl IntoResponse {
    let user_id = extract_user_id(&headers);
    let session = state.store.register_form(payload, &user_id);
    Json(json!({ "status": "registered", "session": session }))
}

async fn sync_form_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<FormSyncRequest>,
) -> impl IntoResponse {
    let user_id = extract_user_id(&headers);
    match state.store.apply_sync_patch(payload, &user_id) {
        Ok(session) => Json(json!({ "status": "synchronized", "session": session })),
        Err(err) => Json(json!({ "status": "error", "message": err })),
    }
}

async fn run_agent_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<RunAgentRequest>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let user_id = extract_user_id(&headers);
    let thread_id = payload.thread_id.clone();
    let run_id = payload
        .run_id
        .clone()
        .unwrap_or_else(|| Uuid::new_v4().to_string());
    let user_message = payload
        .message
        .or_else(|| {
            payload
                .messages
                .and_then(|msgs| msgs.last().map(|m| m.content.clone()))
        })
        .unwrap_or_default();

    let (tx, rx) = mpsc::unbounded_channel::<AgUiEvent>();
    let broadcaster = EventBroadcaster::new(tx);

    let session = state.store.get_or_create(&thread_id, &user_id);
    let app_store = state.store.clone();
    let thread_id_clone = thread_id.clone();
    let run_id_clone = run_id.clone();
    let b_clone = broadcaster.clone();

    tokio::spawn(async move {
        // RUN_STARTED
        b_clone.send(AgUiEvent::RunStarted {
            thread_id: thread_id_clone.clone(),
            run_id: run_id_clone.clone(),
        });

        // Run agent
        let updated_session =
            crate::agent::AgentEngine::execute_turn(session, user_message, b_clone.clone()).await;

        app_store.update_session(updated_session);

        // RUN_FINISHED
        b_clone.send(AgUiEvent::RunFinished {
            thread_id: thread_id_clone,
            run_id: run_id_clone,
        });
    });

    let stream = UnboundedReceiverStream::new(rx).map(|ag_event| {
        let serialized = serde_json::to_string(&ag_event).unwrap_or_default();
        Ok(Event::default().data(serialized))
    });

    Sse::new(stream).keep_alive(KeepAlive::default())
}
