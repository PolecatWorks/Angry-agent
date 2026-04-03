# Suggested Tests for Untested Backend Tools

This document outlines suggested tests for the newly added or updated tools in `agent-be-container/src/agent/tools/generate.py` and `agent-be-container/src/agent/tools/mfe.py`.

## `src/agent/tools/generate.py`
These tests should verify that the tools successfully transform input Pydantic models into the expected `MFEContent` objects.

**Mocking & Setup Notes:**
*   You will need to import the respective Input classes (e.g., `JsonInput`, `MarkdownInput`) to construct the test inputs.
*   The `config: RunnableConfig` argument can be mocked simply by passing an empty dictionary `{}` or a dummy config object, as these functions currently do not utilize the config.

1.  [x] **`generate_mfe_of_json`**
    *   [x] Test happy path: Pass a valid `JsonInput` with some JSON-like dictionary content. Verify the returned `MFEContent` has `provider="mfe1"`, `component="./JsonShowWrapper"`, and the content matches the input.
    *   [x] Test with an empty dictionary as the content payload.

2.  [ ] **`generate_mfe_of_markdown`**
    *   [ ] Test happy path: Pass a `MarkdownInput` with a string of markdown text. Verify the returned `MFEContent` has `provider="mfe1"`, `component="./MarkdownShowWrapper"`, and the content matches the input markdown.

3.  [ ] **`generate_mfe_of_text`**
    *   [ ] Test happy path: Pass a `TextInput` with a plain string. Verify the returned `MFEContent` has `provider="mfe1"`, `component="./TextShowWrapper"`, and the content matches the input text.

4.  [ ] **`generate_mfe_of_personal_data_form`**
    *   [ ] Test happy path with all fields populated: Construct a `PersonalDataForm` with first_name, last_name, email, phone_number, and address. Pass it in `PersonalDataFormInput`. Verify the returned `MFEContent` uses component `./PersonalDataFormWrapper` and preserves all fields.
    *   [ ] Test happy path with partial fields: Construct a `PersonalDataForm` leaving optional fields as `None`. Verify that the tool handles this and returns an `MFEContent` object with those missing fields intact as `None`.

5.  [x] **`generate_mfe_of_mermaid`**
    *   [x] Test happy path: Pass a `MermaidInput` containing a basic mermaid string (e.g., `graph TD; A-->B;`). Verify it returns an `MFEContent` with `component="./MermaidShowWrapper"`.

6.  [x] **`generate_data_visualization`**
    *   [x] Test happy path: Construct a `DataVizInput` with a `DataViz` object containing multiple `Dataset`s, `DataPoint`s, an `x_axis_type` (e.g., "linear"), and a title. Verify the output uses `component="./DataShowWrapper"` and that the data structure is preserved in the output content.

---

## `src/agent/tools/mfe.py`
These tests should verify the BREAD (Browse, Read, Edit, Add, Delete) operations that interact with the LangGraph state.

**Mocking & Setup Notes:**
*   You will need to construct a dummy `AgentState` dictionary. `AgentState` usually contains `visualizations: List[MFEContent]`. You can create a fake state using a `TypedDict` or standard dictionary depending on your state implementation. For example: `mock_state = {"visualizations": [mock_mfe_1, mock_mfe_2]}`.
*   For tools requiring an `InjectedToolCallId`, you can pass a dummy string like `"test_tool_call_123"`.
*   Ensure you import and catch `ToolException` from `langchain_core.tools` where applicable.
*   Verify that functions returning a `Command` object actually return a `Command` with the correct `update` payload.

7.  [ ] **`browse_visualizations`**
    *   [ ] Test happy path: Pass a mock state containing several `MFEContent` items. Verify the tool returns the exact list of visualizations from the state.
    *   [ ] Test empty state: Pass a mock state with an empty list of visualizations. Verify it returns an empty list.

8.  [ ] **`read_visualization`**
    *   [ ] Test happy path: Pass a valid ID that exists in the mocked state. Verify the tool returns the specific `MFEContent` object.
    *   [ ] Test missing ID: Pass an ID that does not exist in the mocked state. Verify the tool raises a `ToolException` with the correct error message.

9.  [x] **`edit_visualization`**
    *   [x] Test happy path: Pass an updated `MFEContent` (with a matching ID to one in the mock state) and a dummy `tool_call_id`. Verify the function returns a `Command` where the `update` dictionary contains `"visualizations"` with the updated data and `"action": "update"`. Verify a `ToolMessage` is included.
    *   [x] Test missing ID: Pass an `MFEContent` whose ID does not exist in the state. Verify the tool raises a `ToolException`.

10. [ ] **`add_visualization`**
    *   [ ] Test happy path: Pass a brand new `MFEContent` object and a dummy `tool_call_id`. Verify the function returns a `Command` with `"action": "add"` in the visualizations update list, and includes the correct `ToolMessage`.

11. [x] **`delete_visualization`**
    *   [x] Test happy path: Pass an ID that exists in the mock state and a dummy `tool_call_id`. Verify the function returns a `Command` with `"action": "delete"` and the correct ID in the visualizations update list, plus the `ToolMessage`.
    *   [x] Test missing ID: Pass an ID that does not exist in the mock state. Verify the tool raises a `ToolException`.
