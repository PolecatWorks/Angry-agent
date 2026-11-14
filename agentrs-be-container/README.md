# agentrs-be-container

High-performance Rust backend for stateful AI orchestration, bidirectional real-time state synchronization using the **AG-UI protocol (over SSE)**, RFC 6902 JSON Patch state delta handling, and concepts from **agent-as-data** and **Graphrag**.

## Tech Stack
- **Language**: Rust
- **Web & SSE Framework**: Tokio, Axum, Tower-HTTP
- **Agent Framework**: rig-core (v0.46+)
- **State Patching**: RFC 6902 JSON Patch (`json-patch`)
- **Protocol**: AG-UI v1.0

## Running
```bash
cargo run
```

## Running Tests
```bash
cargo test
```

## API Endpoints
- `GET /health` - Health status and protocol info
- `GET /api/threads` - List user threads
- `GET /api/threads/{thread_id}` - Get thread history and active form context
- `POST /api/form/register` - Register active MFE form schema and initial state
- `POST /api/form/sync` - Sync human edits from RHS MFE to backend session state via RFC 6902 JSON Patches
- `POST /api/agent/run` - Stream agent reasoning and `STATE_DELTA` AG-UI events via SSE
