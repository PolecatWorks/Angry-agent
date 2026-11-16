# Spec 01: Bidirectional Live MFE Canvas UI (`agent-ui-container`)

- **Status**: `complete`
- **Derived From**: [bidirectional-shared-canvas-mfe-prd.md](../prds/bidirectional-shared-canvas-mfe-prd.md)
- **Target Package**: `agent-ui-container`

---

## 1. Objective
Upgrade `agent-ui-container` (`MfeRenderer`, `VisualizationsPanel`, `ChatWindow`, and `ChatService`) from one-way MFE mounting to a true **Bidirectional Live Shared Canvas** where:
1. Updates to a visualization's `content` apply in place via `MfeCanvasController.applyPatch()` without unmounting the DOM or losing user focus.
2. Direct user edits in the RHS MFE sync silently to the backend (`PATCH /api/threads/{thread_id}/visualizations/{viz_id}`) without spamming synthetic chat messages or triggering unsolicited LLM turns.
3. Clicking or focusing a field/element in the RHS MFE surfaces a **"Point-and-Ask" focus pill** (`🎯 Focused: <label>`) above the chat input and attaches the live MFE state, active selection, and self-describing JSON Schema (`getSchema()`) to `POST /api/chat`.

---

## 2. Component & Service Specifications

### 2.1 `MfeRenderer` (`src/app/components/mfe-renderer/mfe-renderer.ts`)
1. Implements `AfterViewInit`, `OnChanges`, `OnDestroy`.
2. Stores the returned `MfeCanvasController` (or wraps a legacy `() => void` unmount function into an adapter controller).
3. Registers the mounted controller with `ChatService` (`registerCanvasController(this.id, controller)`) so `ChatService` can query `getState()` and `getSchema()` immediately when sending a chat message.
4. **`ngOnChanges(changes: SimpleChanges)`**:
   - If `mfe` or `component` changed after initial mount, unmounts the previous module and mounts the new module.
   - If only `content`, `data`, or `attributions` changed and `this.controller?.applyPatch` is available, calls `this.controller.applyPatch(changes['content']?.currentValue ?? this.content, this.attributions)` **in place without unmounting**.
5. Emits:
   - `@Output() action = new EventEmitter<{ action: string; payload: any }>()` (explicit workflow triggers such as submit).
   - `@Output() stateChange = new EventEmitter<{ state: any; patches: JsonPatchOp[] }>()` (silent human edits).
   - `@Output() selectionChange = new EventEmitter<CanvasSelection | null>()` ("Point-and-Ask" focus context).

### 2.2 `VisualizationsPanel` (`src/app/components/visualizations-panel/visualizations-panel.ts`)
1. Adds `trackByVizId(index: number, viz: Visualization): string` and binds `*ngFor="let viz of visualizations; trackBy: trackByVizId"` in `visualizations-panel.html` so polling `getHistory()` never destroys or recreates existing `MfeRenderer` DOM instances.
2. **`handleMfeStateChange(event: { state: any; patches: JsonPatchOp[] }, vizId: string)`**:
   - Updates the local visualization snapshot and triggers a debounced (`300ms`) call to `this.chatService.patchVisualizationState(this.threadId, vizId, event.state, event.patches)`—never calling `sendMessage()` or triggering an LLM turn.
3. **`handleMfeSelectionChange(selection: CanvasSelection | null, vizId: string)`**:
   - Forwards the focused element selection (`{ ...selection, canvasId: vizId }`) to `this.chatService.setActiveSelection(...)`.

### 2.3 `ChatService` & `ChatWindow` (`src/app/services/chat.service.ts`, `src/app/components/chat-window/chat-window.ts`)
1. `ChatService`:
   - Maintains `activeSelection$` (`BehaviorSubject<CanvasSelection | null>`) and a `Map<string, MfeCanvasController>` of mounted RHS canvas controllers.
   - `patchVisualizationState(threadId: string, vizId: string, content: any, patches?: JsonPatchOp[]): Observable<any>` sends `PATCH ${apiUrl}/threads/${threadId}/visualizations/${vizId}`.
   - `getCanvasContext(): CanvasContextPayload | undefined` collects live `{ visualizations: [{ id, state, schema }], active_selection }` from all mounted controllers.
   - `sendMessage(message, threadId, bypassLearningMode, canvasContext)` includes `canvas_context` in `POST ${apiUrl}/chat`.
2. `ChatWindow`:
   - Subscribes to `chatService.activeSelection$` and renders a dismissible focus chip (`🎯 Focused: {{ activeSelection.label }}`) above the message input in `chat-window.html`, with a `clearSelection()` button.

---

## 3. TDD Test Strategy

### Unit Tests
1. **`mfe-renderer.spec.ts`**:
   - Mounts a remote module returning an `MfeCanvasController`.
   - Verifies that subsequent `ngOnChanges` on `content` calls `controller.applyPatch(...)` in place and does **not** call `unmount()` or re-mount the component.
   - Verifies that `onStateChange` and `onSelectionChange` callbacks passed in `mount(container, props)` emit via `@Output() stateChange` and `@Output() selectionChange`.
2. **`chat.service.spec.ts`**:
   - Verifies `patchVisualizationState()` sends `PATCH /api/threads/{threadId}/visualizations/{vizId}` with `{ content, patches }`.
   - Verifies `sendMessage()` attaches `canvas_context` (including live `getState()`, `getSchema()`, and `active_selection`) to `POST /api/chat`.
3. **`chat-window.spec.ts`**:
   - Verifies that when `chatService.setActiveSelection({ canvasId: 'v1', path: '/email', label: 'Email Address' })` is active, the focus chip is exposed and can be cleared via `clearSelection()`.
