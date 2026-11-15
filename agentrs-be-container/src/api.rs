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
        .route("/api/threads/{thread_id}/history", get(get_thread_history_handler))
        .route("/api/threads/{thread_id}/visualizations", get(get_visualizations_handler))
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

#[derive(Debug, sqlx::FromRow)]
struct ThreadRow {
    user_id: String,
    color: Option<String>,
    status_msg: Option<String>,
    status_updated_at: Option<chrono::DateTime<chrono::Utc>>,
}

#[derive(Debug, sqlx::FromRow)]
struct VisualizationRow {
    id: uuid::Uuid,
    thread_id: String,
    mfe: String,
    component: String,
    content: serde_json::Value,
    description: Option<String>,
    order_index: i32,
    created_at: Option<chrono::DateTime<chrono::Utc>>,
    updated_at: Option<chrono::DateTime<chrono::Utc>>,
    name: Option<String>,
    pin_to_pane: bool,
}

async fn get_visualizations_handler(
    State(state): State<AppState>,
    Path(thread_id): Path<String>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    if let Some(pool) = &state.pool {
        // Check access
        let thread_row = sqlx::query_as::<_, (String,)>(
            "SELECT user_id FROM threads WHERE thread_id = $1",
        )
        .bind(&thread_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e.to_string() }))))?;

        let Some((owner_id,)) = thread_row else {
            return Ok(Json(json!({ "visualizations": [] })));
        };

        if owner_id != user_id {
            let access_row = sqlx::query_as::<_, (i32,)>(
                "SELECT 1 FROM thread_access WHERE thread_id = $1 AND user_id = $2",
            )
            .bind(&thread_id)
            .bind(&user_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e.to_string() }))))?;

            if access_row.is_none() {
                return Ok(Json(json!({ "visualizations": [] })));
            }
        }

        let vis_rows = sqlx::query_as::<_, VisualizationRow>(
            r#"
            SELECT id, thread_id, mfe, component, content, description, order_index, created_at, updated_at, name, pin_to_pane
            FROM visualizations
            WHERE thread_id = $1
            ORDER BY order_index ASC, created_at ASC
            "#,
        )
        .bind(&thread_id)
        .fetch_all(pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e.to_string() }))))?;

        let vis_json: Vec<serde_json::Value> = vis_rows
            .into_iter()
            .map(|v| {
                json!({
                    "id": v.id.to_string(),
                    "thread_id": v.thread_id,
                    "mfe": v.mfe,
                    "component": v.component,
                    "content": v.content,
                    "description": v.description,
                    "order_index": v.order_index,
                    "name": v.name,
                    "pin_to_pane": v.pin_to_pane,
                    "created_at": v.created_at.map(|c| c.to_rfc3339()),
                    "updated_at": v.updated_at.map(|c| c.to_rfc3339()),
                })
            })
            .collect();

        return Ok(Json(json!({ "visualizations": vis_json })));
    }

    Ok(Json(json!({ "visualizations": [] })))
}

async fn get_thread_history_handler(
    State(state): State<AppState>,
    Path(thread_id): Path<String>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, (StatusCode, Json<serde_json::Value>)> {
    let user_id = extract_user_id(&headers);

    if let Some(pool) = &state.pool {
        let thread_row = sqlx::query_as::<_, ThreadRow>(
            "SELECT user_id, color, status_msg, status_updated_at FROM threads WHERE thread_id = $1",
        )
        .bind(&thread_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e.to_string() }))))?;

        let Some(t_row) = thread_row else {
            return Ok(Json(json!({
                "thread": { "thread_id": thread_id },
                "messages": [],
                "visualizations": []
            })));
        };

        if t_row.user_id != user_id {
            let access_row = sqlx::query_as::<_, (i32,)>(
                "SELECT 1 FROM thread_access WHERE thread_id = $1 AND user_id = $2",
            )
            .bind(&thread_id)
            .bind(&user_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({ "error": e.to_string() }))))?;

            if access_row.is_none() {
                return Ok(Json(json!({
                    "thread": { "thread_id": thread_id },
                    "messages": [],
                    "visualizations": []
                })));
            }
        }

        // Fetch visualizations
        let vis_rows = sqlx::query_as::<_, VisualizationRow>(
            r#"
            SELECT id, thread_id, mfe, component, content, description, order_index, created_at, updated_at, name, pin_to_pane
            FROM visualizations
            WHERE thread_id = $1
            ORDER BY order_index ASC, created_at ASC
            "#,
        )
        .bind(&thread_id)
        .fetch_all(pool)
        .await
        .unwrap_or_default();

        let vis_json: Vec<serde_json::Value> = vis_rows
            .into_iter()
            .map(|v| {
                json!({
                    "id": v.id.to_string(),
                    "thread_id": v.thread_id,
                    "mfe": v.mfe,
                    "component": v.component,
                    "content": v.content,
                    "description": v.description,
                    "order_index": v.order_index,
                    "name": v.name,
                    "pin_to_pane": v.pin_to_pane,
                })
            })
            .collect();

        // Build messages list from in-memory session or empty
        let messages_list = state
            .store
            .get(&thread_id)
            .map(|s| {
                s.messages
                    .into_iter()
                    .map(|m| {
                        json!({
                            "type": m.role,
                            "content": m.content,
                            "id": m.id,
                            "created_at": m.created_at,
                        })
                    })
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();

        return Ok(Json(json!({
            "thread": {
                "thread_id": thread_id,
                "user_id": t_row.user_id,
                "color": t_row.color,
                "status_msg": t_row.status_msg,
                "status_updated_at": t_row.status_updated_at.map(|d| d.to_rfc3339()),
                "current_server_time": chrono::Utc::now().to_rfc3339(),
                "learning_mode_enabled": false
            },
            "messages": messages_list,
            "visualizations": vis_json
        })));
    }

    // In-memory fallback
    let session = state.store.get(&thread_id);
    let messages = session
        .as_ref()
        .map(|s| {
            s.messages
                .iter()
                .map(|m| {
                    json!({
                        "type": m.role,
                        "content": m.content,
                        "id": m.id,
                        "created_at": m.created_at,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    Ok(Json(json!({
        "thread": {
            "thread_id": thread_id,
            "user_id": user_id,
            "color": null,
            "status_msg": null,
            "status_updated_at": null,
            "current_server_time": chrono::Utc::now().to_rfc3339(),
            "learning_mode_enabled": false
        },
        "messages": messages,
        "visualizations": []
    })))
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
