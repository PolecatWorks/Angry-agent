use crate::models::AgUiEvent;
use serde_json::Value;
use tokio::sync::mpsc;

#[derive(Clone)]
pub struct EventBroadcaster {
    sender: mpsc::UnboundedSender<AgUiEvent>,
}

impl EventBroadcaster {
    pub fn new(sender: mpsc::UnboundedSender<AgUiEvent>) -> Self {
        Self { sender }
    }

    pub fn send(&self, event: AgUiEvent) {
        let _ = self.sender.send(event);
    }

    pub fn send_text_delta(&self, message_id: &str, delta: &str) {
        self.send(AgUiEvent::TextMessageContent {
            message_id: message_id.to_string(),
            delta: delta.to_string(),
        });
    }

    pub fn send_state_delta(&self, patch: json_patch::Patch) {
        self.send(AgUiEvent::StateDelta { delta: patch });
    }

    pub fn send_custom(&self, name: &str, payload: Value) {
        self.send(AgUiEvent::Custom {
            name: name.to_string(),
            payload,
        });
    }
}
