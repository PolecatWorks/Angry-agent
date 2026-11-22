use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FormContext {
    pub form_id: String,
    pub json_schema: serde_json::Value,
    pub current_data: serde_json::Value,
    pub validation_errors: HashMap<String, Vec<String>>,
    pub focused_field: Option<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum MessageRole {
    User,
    Assistant,
    System,
    Human,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ChatMessage {
    pub id: String,
    pub role: MessageRole,
    pub content: String,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AgentSession {
    pub thread_id: String,
    pub user_id: String,
    pub messages: Vec<ChatMessage>,
    pub active_form: Option<FormContext>,
    pub updated_at: i64,
}

impl AgentSession {
    pub fn new(thread_id: impl Into<String>, user_id: impl Into<String>) -> Self {
        Self {
            thread_id: thread_id.into(),
            user_id: user_id.into(),
            messages: Vec::new(),
            active_form: None,
            updated_at: chrono::Utc::now().timestamp_millis(),
        }
    }
}

/// AG-UI Protocol v1.0 Event Specification
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
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
    ToolCallStart {
        tool_call_id: String,
        tool_name: String,
    },

    #[serde(rename = "TOOL_CALL_ARGS")]
    ToolCallArgs { tool_call_id: String, delta: String },

    #[serde(rename = "TOOL_CALL_END")]
    ToolCallEnd { tool_call_id: String },

    #[serde(rename = "STATE_DELTA")]
    StateDelta { delta: json_patch::Patch },

    #[serde(rename = "CUSTOM")]
    Custom {
        name: String,
        payload: serde_json::Value,
    },

    #[serde(rename = "RUN_FINISHED")]
    RunFinished { thread_id: String, run_id: String },

    #[serde(rename = "ERROR")]
    Error { message: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterFormRequest {
    pub thread_id: String,
    pub form_id: String,
    pub json_schema: serde_json::Value,
    pub initial_data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormSyncRequest {
    pub thread_id: String,
    pub patches: json_patch::Patch,
    #[serde(default)]
    pub validation_errors: HashMap<String, Vec<String>>,
    pub focused_field: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunAgentRequest {
    #[serde(rename = "threadId", alias = "thread_id")]
    pub thread_id: String,
    #[serde(rename = "runId", alias = "run_id")]
    pub run_id: Option<String>,
    #[serde(default)]
    pub message: Option<String>,
    #[serde(default)]
    pub messages: Option<Vec<ChatMessage>>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn message_role_serializes_and_deserializes_lowercase() {
        for (role, expected) in [
            (MessageRole::User, "user"),
            (MessageRole::Assistant, "assistant"),
            (MessageRole::System, "system"),
            (MessageRole::Human, "human"),
        ] {
            let val = serde_json::to_value(role).unwrap();
            assert_eq!(val, json!(expected));
            let roundtrip: MessageRole = serde_json::from_value(val).unwrap();
            assert_eq!(roundtrip, role);
        }

        assert!(serde_json::from_value::<MessageRole>(json!("invalid_role")).is_err());
    }
}
