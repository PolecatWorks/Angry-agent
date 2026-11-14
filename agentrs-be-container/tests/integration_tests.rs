use axum::http::StatusCode;
use axum_test::TestServer;
use serde_json::json;

#[tokio::test]
async fn test_full_agentrs_form_workflow() {
    let store = agentrs_be::session_store::SessionStore::new();
    let state = agentrs_be::api::AppState { store };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    // 1. Check health
    let resp = server.get("/health").await;
    assert_eq!(resp.status_code(), StatusCode::OK);
    let health_json: serde_json::Value = resp.json();
    assert_eq!(health_json["container"], "agentrs-be-container");

    // 2. Register Form
    let register_resp = server
        .post("/api/form/register")
        .add_header("X-User-ID", "test-user-1")
        .json(&json!({
            "thread_id": "thread-abc-123",
            "form_id": "vendor_onboarding_v2",
            "json_schema": {
                "type": "object",
                "properties": {
                    "companyName": { "type": "string" },
                    "vatNumber": { "type": "string" }
                }
            },
            "initial_data": {
                "companyName": "Acme Corp",
                "vatNumber": ""
            }
        }))
        .await;
    assert_eq!(register_resp.status_code(), StatusCode::OK);

    // 3. Sync Human Edits
    let sync_resp = server
        .post("/api/form/sync")
        .add_header("X-User-ID", "test-user-1")
        .json(&json!({
            "thread_id": "thread-abc-123",
            "patches": [
                { "op": "replace", "path": "/companyName", "value": "Acme Global Industries" }
            ],
            "validation_errors": {},
            "focused_field": "/companyName"
        }))
        .await;
    assert_eq!(sync_resp.status_code(), StatusCode::OK);

    // 4. Verify thread state
    let get_thread = server.get("/api/threads/thread-abc-123").await;
    assert_eq!(get_thread.status_code(), StatusCode::OK);
    let thread_json: serde_json::Value = get_thread.json();
    assert_eq!(
        thread_json["session"]["active_form"]["current_data"]["companyName"],
        "Acme Global Industries"
    );
    assert_eq!(
        thread_json["session"]["active_form"]["focused_field"],
        "/companyName"
    );
}
