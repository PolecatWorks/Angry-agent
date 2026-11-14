# SPEC-02: Axum Web API & AG-UI SSE Streaming Layer

## 1. Scope & Objective
Implement the HTTP and Server-Sent Events (SSE) server using Axum, exposing routes for form registration, bidirectional state synchronization, health checks, and streaming agent turns.

## 2. API Endpoints

### 2.1 Health & Diagnostic
- `GET /health`: Returns 200 OK `{"status": "ok", "version": "..."}`.
- `GET /api/threads`: List active threads for the user (`X-User-ID`).
- `GET /api/threads/{thread_id}`: Fetch thread history & active form context.

### 2.2 Form Registration (`POST /api/form/register`)
- Header: `X-User-ID`
- Body:
  ```json
  {
    "thread_id": "string",
    "form_id": "string",
    "json_schema": {},
    "initial_data": {}
  }
  ```
- Effect: Attaches or replaces `active_form` in the `AgentSession`.

### 2.3 Form Synchronization (`POST /api/form/sync`)
- Header: `X-User-ID`
- Body:
  ```json
  {
    "thread_id": "string",
    "patches": [ ...RFC 6902 patch operations... ],
    "validation_errors": { "field": ["err"] },
    "focused_field": "/field"
  }
  ```
- Effect: Applies patches directly to `active_form.current_data`, updates errors and focus pointer. Does not invoke LLM inference.

### 2.4 Agent Execution & Streaming (`POST /api/agent/run`)
- Header: `X-User-ID`
- Body:
  ```json
  {
    "thread_id": "string",
    "run_id": "string",
    "message": "string"
  }
  ```
- Response: `Content-Type: text/event-stream` emitting AG-UI JSON events.

## 3. Concurrency & Header Checks
- Extracts `X-User-ID` (defaults to "default_user" if omitted in dev).
- Tokio channel-based broadcast for SSE event streaming to client.
