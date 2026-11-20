# SPEC-03: Rig Agent Orchestration, Dynamic Tools & Prompt Preamble

## 1. Scope & Objective
Implement the agent orchestrator using `rig-core` (or mockable agent runner when API keys are not supplied in tests), injecting live `FormContext` into the preamble and dynamically exposing tool definitions for RFC 6902 state patching and MFE form switching.

## 2. Dynamic Tool Definitions

### 2.1 DynamicFormPatchTool
- **Parameters**: Dynamic JSON schema taken directly from `active_form.json_schema`.
- **Behavior**: When the agent chooses to modify form fields, it produces the updated or delta fields.
- **Diff Computation**: Computes the RFC 6902 JSON patch between current data and target data.
- **Emission**: Immediately sends a `STATE_DELTA` AG-UI event to the active SSE channel before text completion finishes.

### 2.2 Lifecycle Tools
- `switch_active_form(form_id: String)`:
  - Agent switches active MFE workflow.
  - Emits `CUSTOM` event `{ "name": "LOAD_MFE", "payload": { "form_id": form_id } }`.
- `request_form_submission(summary: String)`:
  - Halts automatic submission; requests user approval.
  - Emits `CUSTOM` event `{ "name": "REQUEST_SUBMIT_APPROVAL", "payload": { "summary": summary } }`.

## 3. Preamble Generation
The agent system prompt dynamically incorporates:
```
You are an intelligent assistant collaborating on an interactive form canvas.
The user is viewing form: {{form_id}}
Current form state: {{current_data}}
Validation errors: {{validation_errors}}
Currently focused field by user: {{focused_field}}

Instructions:
- When the user asks you to fill, update, or correct form fields, use the patch_form tool.
- Respect user focus: Avoid overwriting the focused field unless explicitly requested.
```
