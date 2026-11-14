# SPEC-01: Shared Domain Models, RFC 6902 Patch Engine & Session Store

## 1. Scope & Objective
Establish core domain data structures, the AG-UI v1.0 protocol serialization models, JSON Patch state manipulation routines, and thread-safe session store management in Rust.

## 2. Models Specification

### 2.1 Form Context & Session
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormContext {
    pub form_id: String,
    pub json_schema: serde_json::Value,
    pub current_data: serde_json::Value,
    pub validation_errors: HashMap<String, Vec<String>>,
    pub focused_field: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub id: String,
    pub role: String, // "user", "assistant", "system"
    pub content: String,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentSession {
    pub thread_id: String,
    pub user_id: String,
    pub messages: Vec<ChatMessage>,
    pub active_form: Option<FormContext>,
    pub updated_at: i64,
}
```

### 2.2 AG-UI Protocol Wire Events
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum AgUiEvent {
    #[serde(rename = "RUN_STARTED")]
    RunStarted { thread_id: String, run_id: String },
    
    #[serde(rename = "TEXT_MESSAGE_START")]
    TextMessageStart { message_id: String },
    
    #[serde(rename = "TEXT_MESSAGE_CONTENT")]
    TextMessageContent { message_id: String, delta: String },
    
    #[serde(rename = "TEXT_MESSAGE_END")]
    TextMessageEnd { message_id: String },
    
    #[serde(rename = "TOOL_CALL_START")]
    ToolCallStart { tool_call_id: String, tool_name: String },
    
    #[serde(rename = "TOOL_CALL_ARGS")]
    ToolCallArgs { tool_call_id: String, delta: String },
    
    #[serde(rename = "TOOL_CALL_END")]
    ToolCallEnd { tool_call_id: String },
    
    #[serde(rename = "STATE_DELTA")]
    StateDelta { delta: Vec<json_patch::PatchOperation> },
    
    #[serde(rename = "CUSTOM")]
    Custom { name: String, payload: serde_json::Value },
    
    #[serde(rename = "RUN_FINISHED")]
    RunFinished { thread_id: String, run_id: String },
    
    #[serde(rename = "ERROR")]
    Error { message: String },
}
```

### 2.3 Session Store
- High-concurrency store backed by `DashMap<String, AgentSession>` for in-memory execution.
- Provides operations: `get_session`, `upsert_session`, `register_form`, `apply_sync_patch`.

## 3. Unit Test Requirements
- Verification of RFC 6902 patch computation and application using `json-patch`.
- AG-UI serialization roundtrips.
- Concurrent read/write safety in session store.
