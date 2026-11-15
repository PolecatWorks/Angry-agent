# Product Requirements Document (PRD): agentrs-be-container

## 1. Executive Summary & Vision
`agentrs-be-container` is a high-performance, asynchronous Rust backend designed to replace or complement `agent-be-container`. Powered by **Tokio**, **Axum**, and **rig-core**, it provides stateful AI orchestration, bidirectional real-time state synchronization using the **AG-UI protocol (over SSE)**, RFC 6902 JSON Patch state delta handling, and concepts from:
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
6. **Form Catalog & Sample Forms Management**:
   - Built-in catalog of reference MFE forms (e.g. Vendor Onboarding, Expense Claim) exposing standard Draft 2020-12 JSON Schemas, field constraints, and initial states.
   - API endpoints to list available catalog forms (`GET /api/forms`) and retrieve form definitions by ID (`GET /api/forms/{form_id}`).
7. **Comprehensive Integration Testing & Verification Suite**:
   - End-to-end integration tests validating form lifecycle, human-to-backend RFC 6902 state synchronization, focus collision protection, SSE streaming of AG-UI events, conversational form switching, and submission confirmation guardrails.
   - Robot Framework test suites for container-level validation in deployment pipelines.
8. **Container Independence & Health Monitoring (HaMS)**:
   - Independent Docker container buildable with standard cargo tools, adhering to zero Docker Compose dependency.
   - Built-in integration with PolecatWorks `hams` (Health Monitoring System) library on dedicated health port (default `8078`), providing standard Kubernetes probes (`/hams/alive`, `/hams/ready`, `/hams/startup`, `/hams/metrics`, `/hams/version`).

## 3. Architecture & Tech Stack
- **Language / Runtime**: Rust (Edition 2021/2024, `rustc 1.98+`, Tokio).
- **Web Framework**: Axum, Tower, Tower-HTTP (CORS, Trace, Compression).
- **Agent Framework**: `rig-core` (v0.46+) for LLM orchestration, completions, and dynamic tool execution.
- **State & Patching**: `json-patch` (RFC 6902), `serde`, `serde_json`, `DashMap` (concurrent sessions), `sqlx` (PostgreSQL).
- **Event Streaming**: Axum SSE (`axum::response::sse`) emitting AG-UI v1.0 events.
- **Configuration & Logging**: `tracing`, `tracing-subscriber`, `config` / `dotenvy`.

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
- `SPEC-02-AXUM-API-SSE.md`: HTTP endpoints (`/api/form/register`, `/api/form/sync`, `/api/agent/run`, `/health`).
- `SPEC-03-RIG-AGENT-TOOLS.md`: `rig-core` agent runner, `DynamicFormPatchTool`, preamble generation, lifecycle tools.
- `SPEC-04-PERSISTENCE-GRAPHRAG.md`: PostgreSQL session checkpointing and agent-as-data schema modeling.
- `SPEC-05-FORM-CATALOG-TEST-SUITE.md`: Form catalog registry (`/api/forms`), reference sample forms, and automated integration test specifications.
