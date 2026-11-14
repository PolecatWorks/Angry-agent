use crate::broadcaster::EventBroadcaster;
use crate::catalog::FormCatalog;
use crate::models::{AgUiEvent, FormSyncRequest, RegisterFormRequest, RunAgentRequest};
use crate::session_store::SessionStore;
use axum::{
    extract::{Path, State},
    http::HeaderMap,
    response::sse::{Event, KeepAlive, Sse},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use futures::stream::Stream;
use serde_json::json;
use std::convert::Infallible;
use tokio::sync::mpsc;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tokio_stream::StreamExt;
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    pub store: SessionStore,
    pub catalog: FormCatalog,
}

pub fn create_router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health_handler))
        .route("/api/forms", get(list_forms_handler))
        .route("/api/forms/{form_id}", get(get_form_handler))
        .route("/api/threads", get(list_threads_handler))
        .route("/api/threads/{thread_id}", get(get_thread_handler))
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

async fn list_threads_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> impl IntoResponse {
    let user_id = extract_user_id(&headers);
    let threads = state.store.list_user_sessions(&user_id);
    Json(json!({ "threads": threads }))
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
