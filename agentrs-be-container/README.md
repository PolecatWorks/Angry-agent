# agentrs-be-container

High-performance Rust backend for stateful AI orchestration, bidirectional real-time state synchronization using the **AG-UI protocol (over SSE)**, RFC 6902 JSON Patch state delta handling, and concepts from **agent-as-data** and **Graphrag**.

## Tech Stack
- **Language**: Rust (Edition 2021)
- **Web & SSE Framework**: Tokio, Axum, Tower-HTTP
- **Agent Framework**: rig-core (v0.46+)
- **State Patching**: RFC 6902 JSON Patch (`json-patch`)
- **Protocol**: AG-UI v1.0

## Running
```bash
cargo run
# or from root
make agentrs-be-dev
```

## Running Tests
```bash
cargo test
# or from root
make agentrs-be-test
```

## Integration Tests & Sample Forms
The container includes integration tests under `tests/integration_tests.rs` along with reference sample MFE forms under `tests/sample_forms/`:

1. **Vendor Onboarding Form (`tests/sample_forms/vendor_onboarding_v2.json`)**:
   - Schema-validated form with fields for `companyName`, `country`, `currency`, `vatNumber`, and `notes`.
   - Used in integration testing to verify agent prompt formulation and agent actuation emitting `STATE_DELTA` JSON patches (e.g. populating standard UK VAT defaults).
2. **Corporate Expense Claim Form (`tests/sample_forms/expense_claim_v1.json`)**:
   - Schema-validated form for expense reporting with fields for `claimantName`, `category`, `amount`, and `currency`.
   - Used in integration testing to verify dynamic form switching (`LOAD_MFE`) and submission guardrails (`REQUEST_SUBMIT_APPROVAL`).

### Integration Test Suite:
- `test_full_agentrs_form_workflow`: Verifies health check, form registration via `POST /api/form/register`, human RFC 6902 patch sync via `POST /api/form/sync` with cursor focus tracking, and thread history retrieval.
- `test_sample_vendor_onboarding_form_and_agent_run`: Registers `vendor_onboarding_v2.json`, executes an agent turn with `POST /api/agent/run`, and verifies live AG-UI SSE streaming events (`RUN_STARTED`, `STATE_DELTA`, `RUN_FINISHED`).
- `test_sample_expense_claim_form_switch_and_submission`: Registers `expense_claim_v1.json`, tests conversational form switching, and checks submission confirmation guardrails.

## API Endpoints
- `GET /health` - Health status and protocol info
- `GET /api/threads` - List user threads
- `GET /api/threads/{thread_id}` - Get thread history and active form context
- `POST /api/form/register` - Register active MFE form schema and initial state
- `POST /api/form/sync` - Sync human edits from RHS MFE to backend session state via RFC 6902 JSON Patches
- `POST /api/agent/run` - Stream agent reasoning and `STATE_DELTA` AG-UI events via SSE
