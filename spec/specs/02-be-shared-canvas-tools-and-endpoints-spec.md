# Spec 02: Shared Canvas Backend Endpoints, Reducer & Self-Describing Tools (`agent-be-container`)

- **Status**: `complete`
- **Derived From**: [bidirectional-shared-canvas-mfe-prd.md](../prds/bidirectional-shared-canvas-mfe-prd.md)
- **Target Package**: `agent-be-container`

---

## 1. Objective
Upgrade `agent-be-container` (`src/agent/structs.py`, `src/agent/tools/mfe.py`, `src/agent/__init__.py`, `src/agent/handler.py`, `src/main.py`) so that:
1. Human edits in the RHS MFE can be persisted silently via `PATCH /api/threads/{thread_id}/visualizations/{viz_id}` without triggering an LLM run.
2. `POST /api/chat` accepts optional `canvas_context` (live unsubmitted MFE states, self-describing Draft-07 JSON Schemas, and `active_selection` focus context) and synchronizes them into `AgentState` before the LLM executes.
3. The LangGraph agent has generic, schema-driven canvas tools (`inspect_active_mfe`, `patch_active_mfe`, `switch_active_mfe`) and RFC 6902 JSON Pointer patch support in `visualizations_reducer`.

---

## 2. Backend Contracts & Implementation Details

### 2.1 `src/agent/structs.py`
1. **New Pydantic Models**:
   - `JsonPatchOp(BaseModel)`: `op: Literal["add", "replace", "remove"]`, `path: str`, `value: Any = None`.
   - `AiFieldAttribution(BaseModel)`: `path: str`, `source: Literal["ai", "user"] = "ai"`, `confidence: float | None = None`, `rationale: str | None = None`, `epistemic_status: str | None = None`.
   - `CanvasSelection(BaseModel)`: `canvas_id: str`, `path: str`, `id: str | None = None`, `label: str`, `context: Any = None`.
2. **Extended `MFEContent`**:
   - Adds optional fields:
     - `json_schema: Dict[str, Any] | None = None`
     - `attributions: List[AiFieldAttribution] = Field(default_factory=list)`
3. **Extended `AgentState`**:
   - Adds `active_selection: CanvasSelection | None = None`.
4. **RFC 6902 JSON Pointer Patch Action in `visualizations_reducer`**:
   - Adds `apply_json_patches(target: Any, patches: List[Dict[str, Any]]) -> Any` supporting RFC 6902 `/field` and `/nested/0/field` JSON Pointers (`add`, `replace`, `remove`).
   - Handles `action == "patch"` in `visualizations_reducer`: applies `item["patches"]` in place to `current_list[idx].content` and merges `item.get("attributions")` without wiping out unrelated fields.

### 2.2 Generic Self-Describing Canvas Tools (`src/agent/tools/mfe.py`)
1. **`inspect_active_mfe(id: str | None = None, state: Annotated[AgentState, InjectedState]) -> dict`**:
   - Returns the live `content`, `json_schema`, `attributions`, and `active_selection` for the requested visualization ID (or all active visualizations + focused selection if `id` is omitted).
2. **`patch_active_mfe(id: str, patches: List[JsonPatchOp], attributions: List[AiFieldAttribution] | None = None, state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> Command`**:
   - Validates that visualization `id` exists in `state.visualizations`, then returns a `Command` dispatching `{"action": "patch", "id": id, "patches": [...], "attributions": [...]}` to `visualizations_reducer`.
3. **`switch_active_mfe(provider: str, component: str, name: str, title: str, description: str, initial_content: Dict[str, Any], replace_id: str | None = None, state: Annotated[AgentState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> Command`**:
   - Dynamically mounts a new MFE or replaces an existing visualization (`replace_id`) on the RHS workspace with any federated remote component (`mfe1`, `data-engine`, etc.).

### 2.3 Silent State Sync Endpoint & Chat Context Sync (`src/main.py`, `src/agent/handler.py`, `src/agent/__init__.py`)
1. **`PATCH /api/threads/{thread_id}/visualizations/{viz_id}` (`patch_visualization` in `src/main.py`)**:
   - Accepts `{ "content": {...}, "patches": [...], "json_schema": {...}, "active_selection": {...} }`.
   - Verifies thread ownership/access, updates `AgentState.visualizations` (and `active_selection` if provided) via `llm_handler.update_visualization_state(...)`, and returns `200 OK` with `{ "status": "updated", "visualization": ... }` **without** starting a background LLM run.
2. **`POST /api/chat` (`chat_endpoint` in `src/main.py`)**:
   - Accepts optional `canvas_context` in the request JSON (`{ "visualizations": [...], "active_selection": {...} }`) and syncs live unsubmitted frontend state, schemas, and `active_selection` into `AgentState` prior to running the graph.
3. **LLM System Context Injection (`llm_node` in `src/agent/__init__.py`)**:
   - Includes `state.active_selection` (`### User's Currently Focused Canvas Element (Point-and-Ask Context)`) in the system prompt alongside the pinned visualizations so the LLM can resolve deictic references like *"this field"* or *"convert this column to USD"*.

---

## 3. TDD Test Strategy

### Unit & Integration Tests (`agent-be-container/tests/test_agent_tools_mfe.py`, `tests/test_agent.py`)
1. **RFC 6902 Reducer Patching (`test_visualizations_reducer_patch_action`)**:
   - Verifies `add`, `replace`, and `remove` JSON Pointer operations on top-level and nested dict/list paths in `visualizations_reducer`, preserving untouched fields and recording `AiFieldAttribution` entries.
2. **`inspect_active_mfe`, `patch_active_mfe`, and `switch_active_mfe` Tools**:
   - Verifies happy-path and missing-ID `ToolException` handling for all three tools.
3. **Silent `PATCH /api/threads/{thread_id}/visualizations/{viz_id}` & `canvas_context` in `POST /api/chat`**:
   - Verifies that `PATCH` updates visualization state in-place without invoking the LLM, and that `POST /api/chat` with `canvas_context` updates `active_selection` and live MFE state before invoking the agent.
