# Product Requirements Document (PRD): agent-be-container (`agentrs-be`)

## 1. Executive Summary & Vision
`agent-be-container` (crate `agentrs-be`) is the sole, high-performance, asynchronous Rust backend for Angry-agent (replacing the removed legacy Python `agentpy-be-container`). Powered by **Tokio**, **Axum**, and **rig-core**, it provides stateful AI orchestration, bidirectional real-time state synchronization using the **AG-UI protocol (over SSE)**, RFC 6902 JSON Patch state delta handling, and concepts from:
- **`PolecatWorks/agent-as-data`**: Structuring agent state, tools, context, and capabilities as reactive, schema-validated data representations.
- **`PolecatWorks/Graphrag`**: Document and context relationship graphs stored and indexed in PostgreSQL, enabling semantic and relational context injection into agent sessions.
- **Bidirectional Agentic Form Canvas**: Real-time split-pane collaboration between human direct manipulation in Angular Micro-Frontends (RHS) and conversational agent manipulation (LHS).

## 2. Core Objectives & Goals
1. **High-Performance Asynchronous Agent Orchestration**:
   - Built on Tokio + Axum + `rig-core` (v0.46+) with streaming inference and dynamic tool invocation.
2. **Bidirectional State Synchronization (AG-UI Protocol)**:
   - Incremental state synchronization using RFC 6902 JSON Patches (`STATE_DELTA`).
   - Server-Sent Events (SSE) streaming compliant with AG-UI events (`RUN_STARTED`, `TEXT_MESSAGE_CONTENT`, `TOOL_CALL_*`, `STATE_DELTA`, `CUSTOM`, `RUN_FINISHED`).
3. **Dynamic Schema-Driven Agent Perception**:
   - Dynamically bind active MFE form schemas to `DynamicFormPatchTool` so the agent can inspect and mutate active form fields with exact JSON Schema validation.
   - Inject live form data, validation errors, and user focus state (`focused_field`) into the agent's prompt preamble.
4. **Concurrency & Human-in-the-Loop Safety**:
   - Guard against overwriting actively edited user fields (`focused_field` conflict detection).
   - Require explicit user confirmation for irreversible operations via `request_form_submission`.
5. **Agent-as-Data & GraphRAG Integration**:
   - Model agents, tool definitions, workflows, and form state as queryable data structures.
   - Graph-based context retrieval and persistence in PostgreSQL with in-memory caching (`DashMap`).
6. **Form & Interactive Canvas Catalog Management**:
   - Built-in catalog of reference MFE forms and interactive `data-engine` canvases (`vendor_onboarding_v2`, `expense_claim_v1`, `data_visual_explorer_v1`, `semantic_topology_v1`, `statistical_diagnostics_v1`) exposing standard JSON Schemas, MFE remote coordinates (`data-engine` + `./DataVisualExplorerWrapper`, `./SemanticTopologyWrapper`, `./StatisticalDiagnosticsWrapper`), and initial states.
   - API endpoints to list available catalog entries (`GET /api/forms`) and retrieve definitions by ID (`GET /api/forms/{form_id}`), plus conversational `LOAD_MFE` workspace switching and `STATE_DELTA` patching for chart scale/renderer and topology lens/highlight transitions.
7. **Comprehensive Integration Testing & Verification Suite**:
   - End-to-end integration tests validating form lifecycle, human-to-backend RFC 6902 state synchronization, focus collision protection, SSE streaming of AG-UI events, conversational form switching, and submission confirmation guardrails.
   - Robot Framework test suites for container-level validation in deployment pipelines.
8. **Container Independence & Kubernetes Interchangeability**:
   - Independent Docker container buildable with standard cargo tools, adhering to zero Docker Compose dependency.
    - Built-in drop-in interchangeability with `agent-be-container`:
      - Dedicated `src/cli.rs` (`clap` derive) entrypoint requiring an explicit subcommand (`Commands::Start` or `Commands::Migrate`) and a required `--config <path>` argument (`start --config <path> [--secrets <path>]` and `migrate --action apply|rollback|list --config <path> [--secrets <path>]`), with no top-level optional subcommand or `ServiceConfig::default()` fallback.
      - Port alignment: Web traffic on `8080` (parsed from required `webservice.url` as `url::Url` via `WebServerConfig::port()` using `Url::port_or_known_default()`, supporting path-suffixed URLs such as `http://0.0.0.0:8080/agent-be`), HaMS monitoring on `8079` (`hams.port`, `/hams/alive`, `/hams/ready`, `/hams/startup`, `/hams/metrics`, `/hams/version`), with zero `std::env::var` runtime port or `DATABASE_URL` fallbacks.
      - Fail-fast boot sequence & configuration validation (`ServiceConfig::from_yaml_and_secrets` + `ServiceConfig::validate()` + typed `thiserror` `ConfigError`/`BootError` in `src/error.rs`, without `#[serde(default)]` on required `webservice` configuration): strictly executes `Parse CLI -> Load & validate config (including fail-fast secrets directory check and boot-time RSA PEM validation via DecodingKey::from_rsa_pem) -> Connect PgPool (fatal if DB URL configured and connect fails) -> Run migrations (fatal on error) -> Init stores/catalog/router -> Bind TcpListener -> Start HaMS & flip ready probe (agentrs-ready starts false) -> axum::serve`, exiting non-zero on any failure.
      - Strong boundary typing: URL configuration parsed directly into `url::Url`, path parameters (`viz_id`, `agent_id`) extracted directly via `Path<Uuid>`, and chat message roles modeled via the typed `MessageRole` enum (`user`, `assistant`, `system`, `human`).
      - Typed API & session error propagation (`ApiError` implementing `axum::response::IntoResponse` and `SessionError` in `src/error.rs`): all HTTP handlers propagate database (`sqlx::Error`), JSON (`serde_json::Error`), RFC 6902 patch (`json_patch::PatchError`), and session (`SessionError`) failures via `?` without swallowed errors or `200 OK` error payloads, mapping missing resources to `404 Not Found`, invalid payloads/missing active forms to `400 Bad Request`, failed patch applications to `422 Unprocessable Entity`, unauthorized access to `403 Forbidden`, and lock contention to `409 Conflict`.
      - Reversible `sqlx` schema migrations (`migrations/0001_initial_schema.up.sql` and `0001_initial_schema.down.sql`) embedded via `sqlx::migrate!("./migrations")` covering `threads`, `thread_access`, `users`, `visualizations` (with `name` and `pin_to_pane`), `agent_definitions`, and `user_settings`.
      - Configurable API route prefix via `webservice.prefix` (e.g. `/api/angry-agent/v1`) with backward compatible `/api` fallback.
      - Strict zero-fallback authentication matching `agent-be-container`: verified RS256 Bearer JWTs with required `exp`, `iss`, `aud`, and `sub` claims injected as `AuthenticatedUser` in request extensions (preferred by all API handlers over raw headers; unverified Bearer JWT payloads are never base64-decoded in handlers), failing closed with 401 Unauthorized for unauthenticated requests or invalid tokens, while keeping `/health` public.

## 3. Architecture & Tech Stack
- **Language / Runtime**: Rust (Edition 2021, `rustc 1.98+`, Tokio).
- **Web Framework**: Axum, Tower, Tower-HTTP (CORS, Trace).
- **Agent Framework**: `rig-core` (v0.46+) for LLM orchestration, completions, and dynamic tool execution.
- **State, Patching & Persistence**: `json-patch` (RFC 6902), `serde`, `serde_json`, `DashMap` (concurrent sessions), `sqlx` (PostgreSQL with reversible `sqlx::migrate!` migrations).
- **Event Streaming**: Axum SSE (`axum::response::sse`) emitting AG-UI v1.0 events.
- **CLI, Configuration & Error Handling**: `clap` (`derive` in `src/cli.rs`), `serde_yaml`, `url` (with `serde` feature), typed `thiserror` errors (`ConfigError`, `BootError`, `SessionError`, `ApiError` in `src/error.rs`), `tracing`, `tracing-subscriber`.

## 4. System Flow & Sequence
1. **Form Registration (`POST /api/form/register`)**:
   - Angular MFE shell loads and registers active `form_id`, `json_schema`, and `initial_data`.
2. **Form Synchronization (`POST /api/form/sync`)**:
   - Direct human edits on the RHS MFE compute RFC 6902 JSON Patches and sync to backend state without triggering an LLM turn.
3. **Agent Turn Execution (`POST /api/agent/run` or `/api/chat`)**:
   - User sends a prompt via LHS chat.
   - Backend constructs the agent prompt incorporating `FormContext` and binds `DynamicFormPatchTool`.
   - Backend streams SSE events (`RUN_STARTED`, `STATE_DELTA` when tool triggers, `TEXT_MESSAGE_CONTENT`, `RUN_FINISHED`).
4. **MFE Switching & Actions (`CUSTOM` AG-UI events)**:
   - Agent can invoke `switch_active_form` or `request_form_submission`, translated into AG-UI custom actions for the UI shell.

## 5. Specification Breakdown
Detailed implementation specifications are broken down into:
- `SPEC-01-SHARED-MODELS.md`: Domain models, AG-UI event schemas, RFC 6902 patch processing, Session store.
- `SPEC-02-AXUM-API-SSE.md`: HTTP endpoints (`/api/user/settings`, `/api/threads`, `/api/form/register`, `/api/form/sync`, `/api/agent/run`, `/health`).
- `SPEC-03-RIG-AGENT-TOOLS.md`: `rig-core` agent runner, `DynamicFormPatchTool`, preamble generation, lifecycle tools.
- `SPEC-04-PERSISTENCE-GRAPHRAG.md`: PostgreSQL session checkpointing and agent-as-data schema modeling.
- `SPEC-05-FORM-CATALOG-TEST-SUITE.md`: Form catalog registry (`/api/forms`), reference sample forms, and automated integration test specifications.
