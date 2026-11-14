use axum::http::StatusCode;
use axum_test::TestServer;
use serde_json::{json, Value};

#[tokio::test]
async fn test_full_agentrs_form_workflow() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState { store, catalog };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    // 1. Check health
    let resp = server.get("/health").await;
    assert_eq!(resp.status_code(), StatusCode::OK);
    let health_json: serde_json::Value = resp.json();
    assert_eq!(health_json["container"], "agentrs-be-container");

    // Check catalog endpoints
    let forms_resp = server.get("/api/forms").await;
    assert_eq!(forms_resp.status_code(), StatusCode::OK);
    let forms_json: serde_json::Value = forms_resp.json();
    assert!(forms_json["forms"].as_array().unwrap().len() >= 2);

    let single_form = server.get("/api/forms/vendor_onboarding_v2").await;
    assert_eq!(single_form.status_code(), StatusCode::OK);

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

#[tokio::test]
async fn test_sample_vendor_onboarding_form_and_agent_run() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState { store, catalog };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let vendor_form_str = include_str!("sample_forms/vendor_onboarding_v2.json");
    let vendor_form: Value = serde_json::from_str(vendor_form_str).unwrap();

    let thread_id = "thread-vendor-999";
    let user_id = "user-procurement";

    // Register vendor form
    let reg_resp = server
        .post("/api/form/register")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "form_id": vendor_form["form_id"],
            "json_schema": vendor_form["json_schema"],
            "initial_data": vendor_form["initial_data"],
        }))
        .await;
    assert_eq!(reg_resp.status_code(), StatusCode::OK);

    // Run agent with instruction to populate UK VAT defaults
    let run_resp = server
        .post("/api/agent/run")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "run_id": "run-001",
            "message": "Populate standard UK VAT defaults"
        }))
        .await;
    assert_eq!(run_resp.status_code(), StatusCode::OK);

    let sse_text = run_resp.text();
    // Validate that AG-UI events were emitted in the SSE response
    assert!(sse_text.contains("RUN_STARTED"));
    assert!(sse_text.contains("STATE_DELTA"));
    assert!(sse_text.contains("RUN_FINISHED"));
    assert!(sse_text.contains("GB987654321"));

    // Check that thread's active form received the state patch
    let thread_resp = server.get(&format!("/api/threads/{thread_id}")).await;
    let thread_json: Value = thread_resp.json();
    assert_eq!(
        thread_json["session"]["active_form"]["current_data"]["vatNumber"],
        "GB987654321"
    );
}

#[tokio::test]
async fn test_sample_expense_claim_form_switch_and_submission() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState { store, catalog };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let expense_form_str = include_str!("sample_forms/expense_claim_v1.json");
    let expense_form: Value = serde_json::from_str(expense_form_str).unwrap();

    let thread_id = "thread-expense-555";
    let user_id = "user-finance";

    // 1. Register expense claim form
    let reg_resp = server
        .post("/api/form/register")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "form_id": expense_form["form_id"],
            "json_schema": expense_form["json_schema"],
            "initial_data": expense_form["initial_data"],
        }))
        .await;
    assert_eq!(reg_resp.status_code(), StatusCode::OK);

    // 2. Instruct agent to switch form
    let switch_resp = server
        .post("/api/agent/run")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "message": "Switch to vendor onboarding form"
        }))
        .await;
    assert_eq!(switch_resp.status_code(), StatusCode::OK);
    let switch_sse = switch_resp.text();
    assert!(switch_sse.contains("LOAD_MFE"));
    assert!(switch_sse.contains("vendor_onboarding_v2"));

    // 3. Request form submission (commit guardrail test)
    let submit_resp = server
        .post("/api/agent/run")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "message": "Submit the form now"
        }))
        .await;
    assert_eq!(submit_resp.status_code(), StatusCode::OK);
    let submit_sse = submit_resp.text();
    assert!(submit_sse.contains("REQUEST_SUBMIT_APPROVAL"));
}
