use crate::models::{AgentSession, FormContext, FormSyncRequest, RegisterFormRequest};
use dashmap::DashMap;
use std::sync::Arc;

#[derive(Clone, Default)]
pub struct SessionStore {
    sessions: Arc<DashMap<String, AgentSession>>,
}

impl SessionStore {
    pub fn new() -> Self {
        Self {
            sessions: Arc::new(DashMap::new()),
        }
    }

    pub fn get_or_create(&self, thread_id: &str, user_id: &str) -> AgentSession {
        self.sessions
            .entry(thread_id.to_string())
            .or_insert_with(|| AgentSession::new(thread_id, user_id))
            .clone()
    }

    pub fn get(&self, thread_id: &str) -> Option<AgentSession> {
        self.sessions.get(thread_id).map(|s| s.clone())
    }

    pub fn register_form(&self, req: RegisterFormRequest, user_id: &str) -> AgentSession {
        let mut session = self
            .sessions
            .entry(req.thread_id.clone())
            .or_insert_with(|| AgentSession::new(&req.thread_id, user_id));

        session.active_form = Some(FormContext {
            form_id: req.form_id,
            json_schema: req.json_schema,
            current_data: req.initial_data,
            validation_errors: std::collections::HashMap::new(),
            focused_field: None,
        });
        session.updated_at = chrono::Utc::now().timestamp_millis();
        session.clone()
    }

    pub fn apply_sync_patch(
        &self,
        req: FormSyncRequest,
        user_id: &str,
    ) -> Result<AgentSession, String> {
        let mut session = self
            .sessions
            .entry(req.thread_id.clone())
            .or_insert_with(|| AgentSession::new(&req.thread_id, user_id));

        if let Some(ref mut form) = session.active_form {
            // Apply RFC 6902 patch
            json_patch::patch(&mut form.current_data, &req.patches)
                .map_err(|e| format!("Failed to apply patch: {e}"))?;

            form.validation_errors = req.validation_errors;
            form.focused_field = req.focused_field;
            session.updated_at = chrono::Utc::now().timestamp_millis();
            Ok(session.clone())
        } else {
            Err("No active form registered for this thread".to_string())
        }
    }

    pub fn list_user_sessions(&self, user_id: &str) -> Vec<AgentSession> {
        self.sessions
            .iter()
            .filter(|entry| entry.value().user_id == user_id)
            .map(|entry| entry.value().clone())
            .collect()
    }

    pub fn update_session(&self, session: AgentSession) {
        self.sessions.insert(session.thread_id.clone(), session);
    }

    pub fn remove(&self, thread_id: &str) -> Option<AgentSession> {
        self.sessions.remove(thread_id).map(|(_, s)| s)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_register_and_patch_sync() {
        let store = SessionStore::new();
        let thread_id = "test-thread-1";
        let user_id = "user-1";

        store.register_form(
            RegisterFormRequest {
                thread_id: thread_id.into(),
                form_id: "vendor_onboarding".into(),
                json_schema: json!({ "type": "object" }),
                initial_data: json!({ "companyName": "Acme Corp", "vatNumber": "123" }),
            },
            user_id,
        );

        let session = store.get(thread_id).expect("Session exists");
        let active_form = session.active_form.expect("Active form exists");
        assert_eq!(active_form.current_data["companyName"], "Acme Corp");

        // Sync a patch modifying vatNumber
        let patch_json = json!([
            { "op": "replace", "path": "/vatNumber", "value": "GB999999" }
        ]);
        let patch: json_patch::Patch = serde_json::from_value(patch_json).unwrap();

        let updated = store
            .apply_sync_patch(
                FormSyncRequest {
                    thread_id: thread_id.into(),
                    patches: patch,
                    validation_errors: Default::default(),
                    focused_field: Some("/vatNumber".into()),
                },
                user_id,
            )
            .unwrap();

        assert_eq!(
            updated.active_form.as_ref().unwrap().current_data["vatNumber"],
            "GB999999"
        );
        assert_eq!(
            updated
                .active_form
                .as_ref()
                .unwrap()
                .focused_field
                .as_deref(),
            Some("/vatNumber")
        );
    }
}
