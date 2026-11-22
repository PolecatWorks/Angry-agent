use crate::broadcaster::EventBroadcaster;
use crate::models::{AgentSession, ChatMessage};
use serde_json::{json, Value};
use uuid::Uuid;

pub struct AgentEngine;

impl AgentEngine {
    /// Formulates prompt preamble incorporating active form state, user focus, and errors
    pub fn build_system_preamble(session: &AgentSession) -> String {
        let mut preamble = String::from(
            "You are an intelligent assistant collaborating with a human on an interactive bidirectional Form Canvas.\n",
        );

        if let Some(ref form) = session.active_form {
            preamble.push_str(&format!(
                "\n--- ACTIVE FORM CONTEXT ---\nForm ID: {}\nSchema: {}\nCurrent Form State: {}\nValidation Errors: {}\nCurrently Focused Field by User: {}\n---------------------------\n",
                form.form_id,
                serde_json::to_string(&form.json_schema).unwrap_or_default(),
                serde_json::to_string_pretty(&form.current_data).unwrap_or_default(),
                serde_json::to_string(&form.validation_errors).unwrap_or_default(),
                form.focused_field.as_deref().unwrap_or("none")
            ));
            preamble.push_str(
                "\nInstructions:\n\
                - To update or fill form fields, you can emit state patches or commands.\n\
                - If the user is currently focused on a field, avoid overwriting it unless requested.\n\
                - You can switch active forms by requesting a form switch.\n\
                - Before irreversible submission, request explicit user confirmation.\n",
            );
        } else {
            preamble.push_str("\nNo form is currently active in the workspace.\n");
        }

        preamble
    }

    /// Run the agent turn and emit streaming AG-UI events
    pub async fn execute_turn(
        mut session: AgentSession,
        user_message: String,
        broadcaster: EventBroadcaster,
    ) -> AgentSession {
        let message_id = Uuid::new_v4().to_string();

        // 1. Text Message Start
        broadcaster.send(crate::models::AgUiEvent::TextMessageStart {
            message_id: message_id.clone(),
        });

        // 2. Inspect intent and dynamic tool actuation
        // Supports automatic simulation / offline execution or LLM integration
        let lower = user_message.to_lowercase();

        if lower.contains("switch to")
            || lower.contains("switch form")
            || lower.contains("open data explorer")
            || lower.contains("open topology")
            || lower.contains("show topology")
            || lower.contains("show chart")
        {
            let (target_form, mfe_coords): (&str, Option<(&str, &str)>) =
                if lower.contains("topology") || lower.contains("semantic graph") {
                    (
                        "semantic_topology_v1",
                        Some(("data-engine", "./SemanticTopologyWrapper")),
                    )
                } else if lower.contains("explorer") || lower.contains("visual") || lower.contains("chart") {
                    (
                        "data_visual_explorer_v1",
                        Some(("data-engine", "./DataVisualExplorerWrapper")),
                    )
                } else if lower.contains("statistical") || lower.contains("diagnostics") {
                    (
                        "statistical_diagnostics_v1",
                        Some(("data-engine", "./StatisticalDiagnosticsWrapper")),
                    )
                } else if lower.contains("vendor") {
                    ("vendor_onboarding_v2", None)
                } else if lower.contains("expense") {
                    ("expense_claim_v1", None)
                } else {
                    ("general_inquiry", None)
                };

            let mut payload = json!({
                "form_id": target_form,
                "reason": "User requested workspace switch"
            });
            if let Some((mfe, component)) = mfe_coords {
                payload["mfe"] = json!(mfe);
                payload["component"] = json!(component);
            }

            broadcaster.send_custom("LOAD_MFE", payload);
            broadcaster.send_text_delta(
                &message_id,
                &format!("Switching active workspace to {}.", target_form),
            );
        } else if lower.contains("submit") || lower.contains("submit form") {
            broadcaster.send_custom(
                "REQUEST_SUBMIT_APPROVAL",
                json!({ "summary": "Ready to submit the current form data." }),
            );
            broadcaster.send_text_delta(
                &message_id,
                "I have prepared the form for submission. Please confirm on the interactive card to proceed.",
            );
        } else if (lower.contains("populate")
            || lower.contains("set")
            || lower.contains("fill")
            || lower.contains("vat")
            || lower.contains("log scale")
            || lower.contains("echarts")
            || lower.contains("field anatomy")
            || lower.contains("er join"))
            && session.active_form.is_some()
        {
            // Simulate agent patch generation
            let mut patches_vec = Vec::new();
            let active_id = session
                .active_form
                .as_ref()
                .map(|f| f.form_id.as_str())
                .unwrap_or_default();

            if active_id == "data_visual_explorer_v1" && (lower.contains("log scale") || lower.contains("echarts")) {
                if lower.contains("log scale") {
                    patches_vec.push(json!({
                        "op": "replace",
                        "path": "/spec/encoding/y/scale/type",
                        "value": "log"
                    }));
                }
                if lower.contains("echarts") {
                    patches_vec.push(json!({
                        "op": "replace",
                        "path": "/renderer",
                        "value": "echarts"
                    }));
                }
            } else if active_id == "semantic_topology_v1" && (lower.contains("field anatomy") || lower.contains("er join")) {
                let next_lens = if lower.contains("field anatomy") {
                    "field_anatomy"
                } else {
                    "er_join"
                };
                patches_vec.push(json!({
                    "op": "replace",
                    "path": "/lens",
                    "value": next_lens
                }));
            } else if lower.contains("vat") || lower.contains("uk") {
                patches_vec.push(json!({
                    "op": "replace",
                    "path": "/vatNumber",
                    "value": "GB987654321"
                }));
                patches_vec.push(json!({
                    "op": "replace",
                    "path": "/currency",
                    "value": "GBP"
                }));
            } else {
                patches_vec.push(json!({
                    "op": "add",
                    "path": "/notes",
                    "value": "Updated by conversational agent."
                }));
            }

            let patch_json = Value::Array(patches_vec);
            if let Ok(patch) = serde_json::from_value::<json_patch::Patch>(patch_json) {
                // Apply locally to session
                if let Some(ref mut form) = session.active_form {
                    let _ = json_patch::patch(&mut form.current_data, &patch);
                }
                // Emit STATE_DELTA
                broadcaster.send_state_delta(patch);
            }

            broadcaster.send_text_delta(
                &message_id,
                "I have updated the active workspace state according to your request.",
            );
        } else {
            // General conversational query (e.g. "what is currently in the form?")
            if lower.contains("what is") || lower.contains("current") {
                if let Some(ref form) = session.active_form {
                    let summary = format!(
                        "The currently active form is '{}'. Its data is:\n{}",
                        form.form_id,
                        serde_json::to_string_pretty(&form.current_data).unwrap_or_default()
                    );
                    broadcaster.send_text_delta(&message_id, &summary);
                } else {
                    broadcaster.send_text_delta(&message_id, "There is no form currently active.");
                }
            } else {
                broadcaster.send_text_delta(
                    &message_id,
                    "I am ready to help you inspect, populate, or validate your form. How would you like to proceed?",
                );
            }
        }

        // 3. Text Message End
        broadcaster.send(crate::models::AgUiEvent::TextMessageEnd { message_id });

        // Record messages into session
        let now = chrono::Utc::now().timestamp_millis();
        session.messages.push(ChatMessage {
            id: Uuid::new_v4().to_string(),
            role: "user".into(),
            content: user_message,
            created_at: now,
        });

        session.updated_at = now;
        session
    }
}
