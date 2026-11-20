use axum::http::StatusCode;
use axum_test::TestServer;
use serde_json::{json, Value};

#[tokio::test]
async fn test_full_agentrs_form_workflow() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: None,
    };
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
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: None,
    };
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
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: None,
    };
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

#[test]
fn test_hams_health_and_probes() {
    let mut hams = agentrs_be::hams::init_hams(8077).expect("Failed to initialize HaMS");
    hams.start().expect("Failed to start HaMS");
    hams.stop().expect("Failed to stop HaMS");
}

#[tokio::test]
async fn test_user_settings_api() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let pool = agentrs_be::db::create_pool().await.ok();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: pool.clone(),
    };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    // 1. Get user settings
    let resp = server
        .get("/api/user/settings")
        .add_header("X-User-ID", "test-settings-user")
        .await;
    assert_eq!(resp.status_code(), StatusCode::OK);
    let initial_json: serde_json::Value = resp.json();
    assert!(initial_json.get("learning_mode_enabled").is_some());

    // 2. Put user settings
    let put_resp = server
        .put("/api/user/settings")
        .add_header("X-User-ID", "test-settings-user")
        .json(&json!({
            "learning_mode_enabled": true
        }))
        .await;
    assert_eq!(put_resp.status_code(), StatusCode::OK);
    let put_json: serde_json::Value = put_resp.json();
    assert_eq!(put_json["status"], "updated");

    // 3. Verify get reflects update if db is connected
    if pool.is_some() {
        let resp_after = server
            .get("/api/user/settings")
            .add_header("X-User-ID", "test-settings-user")
            .await;
        assert_eq!(resp_after.status_code(), StatusCode::OK);
        let after_json: serde_json::Value = resp_after.json();
        assert_eq!(
            after_json.get("learning_mode_enabled").unwrap(),
            &json!(true)
        );
    }
}

#[tokio::test]
async fn test_thread_crud_lifecycle() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let pool = agentrs_be::db::create_pool().await.ok();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: pool.clone(),
    };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let user_id = "test-thread-crud-user";
    let thread_id = "test-thread-uuid-1";

    if let Some(ref p) = pool {
        // Seed a thread directly in db for test
        let _ = sqlx::query(
            "INSERT INTO threads (thread_id, user_id, title, color) VALUES ($1, $2, $3, $4) ON CONFLICT (thread_id) DO UPDATE SET title = EXCLUDED.title"
        )
        .bind(thread_id)
        .bind(user_id)
        .bind("Original Title")
        .bind("#123456")
        .execute(p)
        .await;

        // 1. List threads
        let list_resp = server
            .get("/api/threads")
            .add_header("X-User-ID", user_id)
            .await;
        assert_eq!(list_resp.status_code(), StatusCode::OK);
        let list_json: serde_json::Value = list_resp.json();
        assert!(list_json.get("threads").is_some());

        // 2. Update thread
        let update_resp = server
            .put(&format!("/api/threads/{thread_id}"))
            .add_header("X-User-ID", user_id)
            .json(&json!({
                "title": "Updated Thread Title",
                "color": "#abcdef"
            }))
            .await;
        assert_eq!(update_resp.status_code(), StatusCode::OK);
        let update_json: serde_json::Value = update_resp.json();
        assert_eq!(update_json["status"], "updated");

        // 3. Delete thread
        let delete_resp = server
            .delete(&format!("/api/threads/{thread_id}"))
            .add_header("X-User-ID", user_id)
            .await;
        assert_eq!(delete_resp.status_code(), StatusCode::OK);
        let delete_json: serde_json::Value = delete_resp.json();
        assert_eq!(delete_json["status"], "deleted");

        // 4. Delete again should return 404
        let delete_again = server
            .delete(&format!("/api/threads/{thread_id}"))
            .add_header("X-User-ID", user_id)
            .await;
        assert_eq!(delete_again.status_code(), StatusCode::NOT_FOUND);
    }
}

#[tokio::test]
async fn test_thread_history_and_visualizations_api() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let pool = agentrs_be::db::create_pool().await.ok();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: pool.clone(),
    };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let user_id = "test-vis-user";
    let thread_id = "test-thread-vis-1";

    if let Some(ref p) = pool {
        let _ = sqlx::query(
            "INSERT INTO threads (thread_id, user_id, title, color) VALUES ($1, $2, $3, $4) ON CONFLICT (thread_id) DO NOTHING"
        )
        .bind(thread_id)
        .bind(user_id)
        .bind("Vis Thread")
        .bind("#ff00ff")
        .execute(p)
        .await;

        let vis_id = uuid::Uuid::new_v4();
        let _ = sqlx::query(
            r#"
            INSERT INTO visualizations (id, thread_id, mfe, component, content, description, order_index, name, pin_to_pane)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            "#
        )
        .bind(vis_id)
        .bind(thread_id)
        .bind("mfe-form")
        .bind("FormComponent")
        .bind(json!({ "field": "value" }))
        .bind("Sample Description")
        .bind(0)
        .bind("Test Vis")
        .bind(true)
        .execute(p)
        .await;
    }

    // 1. Get visualizations
    let vis_resp = server
        .get(&format!("/api/threads/{thread_id}/visualizations"))
        .add_header("X-User-ID", user_id)
        .await;
    assert_eq!(vis_resp.status_code(), StatusCode::OK);
    let vis_json: serde_json::Value = vis_resp.json();
    assert!(vis_json.get("visualizations").is_some());

    // 2. Get history
    let hist_resp = server
        .get(&format!("/api/threads/{thread_id}/history"))
        .add_header("X-User-ID", user_id)
        .await;
    assert_eq!(hist_resp.status_code(), StatusCode::OK);
    let hist_json: serde_json::Value = hist_resp.json();
    assert!(hist_json.get("thread").is_some());
    assert!(hist_json.get("messages").is_some());
    assert!(hist_json.get("visualizations").is_some());
}

#[tokio::test]
async fn test_chat_endpoint_lifecycle() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let pool = agentrs_be::db::create_pool().await.ok();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool,
    };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let user_id = "test-chat-user";
    let thread_id = format!("test-chat-thread-{}", uuid::Uuid::new_v4());

    // 1. Send chat message
    let resp = server
        .post("/api/chat")
        .add_header("X-User-ID", user_id)
        .json(&json!({
            "thread_id": thread_id,
            "message": "Hello from integration test"
        }))
        .await;
    assert_eq!(resp.status_code(), StatusCode::ACCEPTED);
    let json_body: serde_json::Value = resp.json();
    assert_eq!(json_body["thread_id"], thread_id);
    assert_eq!(json_body["status"], "processing");
}

#[tokio::test]
async fn test_agent_definitions_crud() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let pool = agentrs_be::db::create_pool().await.ok();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: pool.clone(),
    };
    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    // 1. Create agent
    let create_resp = server
        .post("/api/agents")
        .json(&json!({
            "name": "Integration Test Agent",
            "content": "You are a test agent definition."
        }))
        .await;
    assert_eq!(create_resp.status_code(), StatusCode::CREATED);
    let create_json: serde_json::Value = create_resp.json();
    let agent_id = create_json["id"].as_str().unwrap().to_string();
    assert_eq!(create_json["name"], "Integration Test Agent");

    // Only verify DB-dependent operations if database connection is available
    if pool.is_some() {
        // 2. List agents
        let list_resp = server.get("/api/agents").await;
        assert_eq!(list_resp.status_code(), StatusCode::OK);
        let list_json: serde_json::Value = list_resp.json();
        assert!(list_json
            .as_array()
            .unwrap()
            .iter()
            .any(|a| a["id"] == agent_id));

        // 3. Update agent
        let update_resp = server
            .put(&format!("/api/agents/{agent_id}"))
            .json(&json!({
                "name": "Updated Agent Name",
                "content": "Updated content"
            }))
            .await;
        assert_eq!(update_resp.status_code(), StatusCode::OK);
        let update_json: serde_json::Value = update_resp.json();
        assert_eq!(update_json["name"], "Updated Agent Name");

        // 4. Delete agent
        let delete_resp = server.delete(&format!("/api/agents/{agent_id}")).await;
        assert_eq!(delete_resp.status_code(), StatusCode::OK);
        let delete_json: serde_json::Value = delete_resp.json();
        assert_eq!(delete_json["status"], "deleted");

        // 5. Delete again should return 404
        let delete_again = server.delete(&format!("/api/agents/{agent_id}")).await;
        assert_eq!(delete_again.status_code(), StatusCode::NOT_FOUND);
    }
}

#[tokio::test]
async fn test_prefixed_routing_and_auth_middleware() {
    use agentrs_be::auth::auth_middleware;
    use agentrs_be::config::AuthConfig;
    use std::sync::Arc;

    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: None,
    };

    let auth_config = Arc::new(Some(AuthConfig {
        jwt_public_key: "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqcAgTagDgfhm3VCxV4FA\nWl3Yos4/f9xyFNkJwkudV4b52KcLSHomBEVFfIb65CnSJUHIs8E0vLda3wmZTNdc\nld9K7a4stkfItDGd1JJKqAZNiYlWkgwwMj+TeQUt4mbiVUvt2KZY78r4RlrKE1w7\nGuzs711R/HZz7mz4FFiNAR4GRynZHH6BLbIJA8EJ+JvtRJZ59tybWpuZt5bUUbxv\n9V1fQsF2HR6jCvt/OnctqarMfHm3B/0Ko0EtXCNhzJIqlByvw1n8u0pDEMoLUkOv\neXvigynPOk29FEEYji+UOEvZZHMpMHqgZukUr9dDKYysj18mr06zgpy9HWxEXU1J\n4wIDAQAB\n-----END PUBLIC KEY-----".to_string(),
        jwt_issuer: "https://keycloak.example.com/realms/test".to_string(),
        jwt_audience: "angry-agent-api".to_string(),
    }));

    let app = agentrs_be::api::create_prefixed_router(state, "/api/angry-agent/v1")
        .layer(axum::middleware::from_fn(auth_middleware))
        .layer(axum::Extension(auth_config));

    let server = TestServer::new(app).unwrap();

    // 1. Health check should remain public under /health and /api/angry-agent/v1/health
    let resp1 = server.get("/health").await;
    assert_eq!(resp1.status_code(), StatusCode::OK);

    let resp2 = server.get("/api/angry-agent/v1/health").await;
    assert_eq!(resp2.status_code(), StatusCode::OK);

    // 2. Protected endpoint without token should return 401 Unauthorized
    let resp_no_auth = server.get("/api/angry-agent/v1/threads").await;
    assert_eq!(resp_no_auth.status_code(), StatusCode::UNAUTHORIZED);

    // 3. Protected endpoint with invalid bearer token should return 401
    let resp_bad_token = server
        .get("/api/angry-agent/v1/threads")
        .add_header("Authorization", "Bearer invalid-jwt-token")
        .await;
    assert_eq!(resp_bad_token.status_code(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_patch_visualization_endpoint() {
    let store = agentrs_be::session_store::SessionStore::new();
    let catalog = agentrs_be::catalog::FormCatalog::new();
    let state = agentrs_be::api::AppState {
        store,
        catalog,
        pool: None,
    };

    let app = agentrs_be::api::create_router(state);
    let server = TestServer::new(app).unwrap();

    let patch_resp = server
        .patch("/api/threads/thread-101/visualizations/00000000-0000-0000-0000-000000000001")
        .add_header("X-User-ID", "test-user")
        .json(&json!({
            "content": { "title": "Updated Canvas Content" }
        }))
        .await;

    assert_eq!(patch_resp.status_code(), StatusCode::OK);
    let patch_json: serde_json::Value = patch_resp.json();
    assert_eq!(patch_json["status"], "updated");
    assert_eq!(patch_json["visualization"]["id"], "00000000-0000-0000-0000-000000000001");
}
