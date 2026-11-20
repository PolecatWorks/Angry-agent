# Agent Backend Container Specification (PRD)

## 1. Introduction

The `agent-be-container` is the core logic and intelligence layer of the AI Agent application. It provides an asynchronous web API for the frontend UI, processing user requests using stateful AI agents powered by LangGraph, and persistently storing chat histories and agent checkpoints in a PostgreSQL database.

## 2. Goals

- Provide robust, asynchronous API endpoints to interact with AI agents.
- Retain session and chat history across multiple interactions using PostgreSQL checkpointing.
- Offer dynamic multi-user isolation.
- Support a modular, performant architecture suitable for running as a standalone Docker container, without dependency on Docker Compose.
- Ensure high test coverage and reliability of AI and routing logic.

## 3. Architecture & Tech Stack

- **Framework:** Aiohttp (asynchronous web server).
- **Dependency Management:** Poetry.
- **AI Framework:** LangChain & LangGraph.
- **Language Model:** Configurable, defaulting to `langchain-google-genai`.
- **Database:** PostgreSQL (for state persistence, user histories, and LangGraph checkpoints).

## 4. Features & Functionality

### 4.1 LangGraph AI Agent Execution
The backend uses LangGraph to define and execute agent logic.
- Models and graphs **must be constructed on application startup** (e.g., using a handler class) rather than per request to optimize execution performance and memory footprint.
- Incoming API requests trigger the execution of these pre-constructed graphs.

### 4.2 System Prompt Configuration
The agent's personality and instructions are managed via system prompts.
- These are configurable via a `ServiceConfig` module (defaulting to 'You are a helpful assistant.') and are passed to the agent handler at the time of application startup.

### 4.3 Multi-User Isolation & State Checkpointing
The backend securely manages and isolates the state of individual users.
- Authentication requires verified RS256 Bearer JWTs with required `exp`, `iss`, `aud`, and `sub` claims loaded via `ServiceConfig.auth`. Unauthenticated requests or requests with client-controlled identity headers (`X-User-ID`, fake unsigned JWTs) fail closed with 401 Unauthorized.
- LangGraph integrates directly with a PostgreSQL backend to manage check-pointing.
- **Unified State Management**: All session data, including chat history and the current workspace of pinned visualizations, is stored within the `AgentState`. This state is persisted across requests using LangGraph's PostgreSQL checkpointing mechanism, eliminating the need for separate database tables for visualization metadata.

### 4.4 Intent Routing Logic & Post-Processing
The backend includes specific routing and post-processing mechanisms for processing messages.
- **Intent Routing**: Messages containing simple greetings (like 'hello') can be intercepted and handled directly. Specific keywords (e.g., 'draw', 'picture', 'image') are routed to an `image_node`.
- **LLM Node & Tool-Call Recovery**: The `llm_node` handles primary agent logic and includes a repair mechanism for "lost" tool calls. If the LLM places a valid tool-call JSON structure within its message content instead of using the formal tool-calling API, the node manually injects these as tool calls before the `post_process` stage to ensure consistency.
- **MFE Tool Support**: The agent has access to a variety of tools to manage and generate Micro-Frontend (MFE) components.
    - **Stateful Tools (BREAD)**: Tools like `add_visualization`, `edit_visualization`, and `delete_visualization` return LangGraph `Command` objects. These commands trigger the `visualizations_reducer` to update the `AgentState.visualizations` list directly.
    - **Visualizations Reducer**: A deterministic reducer that manages the workspace list. It supports granular actions: `add` (append), `update` (modify in-place), `delete` (remove), `reorder` (based on a list of IDs), and `replace` (full list override).
- **Post-Process Node**: A deterministic Python-based node that runs after the LLM/Tool loop to finalize the response.
    - **Workspace Summary**: If new visualizations were successfully pinned during the turn, the node appends a summary list to the final AI message content.
    - **Finalization**: It marks the final AIMessage with `packaged: True` and a `timestamp` in `additional_kwargs` to signal completion to the frontend polling client.
- **MFE Tools**:
    - **Workspace Management (BREAD)**:
        - `browse_visualizations`: Lists all currently pinned items from the state.
        - `read_visualization`: Retrieves full details of a specific item from the state.
        - `add_visualization`: Pins a new visualization to the workspace via a `Command`.
        - `edit_visualization`: Updates or reorders an existing visualization via a `Command`.
        - `delete_visualization`: Removes an item from the workspace via a `Command`.
    - **Content Generation**:
        - `generate_mfe_of_markdown`: For rendering markdown text.
        - `generate_mfe_of_text`: For rendering plain text.
        - `generate_mfe_of_json`: For general JSON/structured data.
        - `generate_data_visualization`: For interactive charts.
        - `generate_mfe_of_mermaid` and `visualize_graph`: For Mermaid diagrams.
    - **Generic Bidirectional Shared Canvas Tools & Ecosystem MCP Integration** (see [Bidirectional Shared Canvas PRD](../../spec/prds/bidirectional-shared-canvas-mfe-prd.md) and [Semantic Steward & Provenance Journey PRD](../../spec/prds/semantic-steward-and-provenance-journey-prd.md)):
        - `inspect_active_mfe`: Reads the current live state, focused selection, and self-describing Draft-07 JSON Schema of any mounted RHS MFE form.
        - `patch_active_mfe`: Applies fine-grained RFC 6902 JSON Patch operations (`add`, `replace`, `remove`) and AI provenance attributions to a mounted MFE via the `"patch"` action in `visualizations_reducer`.
        - `switch_active_mfe`: Dynamically switches the RHS workspace between federated MFE applications (including `data-engine`'s `./DataAssetFormWrapper`, `./JoinHypothesisReviewWrapper`, `./AlgorithmSandboxWrapper`, and `./ProvenanceLineageWrapper`).
        - Connects to `Graphrag` (`/api/v1/mcp`), `data-engine` (`/api/v1/mcp`), and `agent-as-data` (`/mcp`) via `MultiServerMCPClient` (`myai.toolbox.mcps`).

## 6. API Interface Expectations
### 6.1 Configurable API Prefix & VirtualService Composition
- The backend supports a configurable API route prefix via `webservice.prefix` in `ServiceConfig` (configured in Kubernetes deployments as `/api/angry-agent/v1`).
- By serving API endpoints directly under `{api_prefix}` (e.g., `/api/angry-agent/v1`), the service integrates with an Istio `VirtualService` **without requiring URI path rewrites**.
- Health checks are registered at both root `/health` and `{api_prefix}/health` (in addition to `/hams/*` on the dedicated HaMS port) so Kubernetes readiness/liveness probes remain stable regardless of prefix changes.

### 6.2 Chat, Threads & Agents
- The service exposes endpoints for the frontend under the configured `{api_prefix}` (e.g., `/api/angry-agent/v1`, with backward-compatible mounting at `/api` when no `/api` prefix is specified):
    - `POST {api_prefix}/chat`: Submit user messages to the agent.
    - `GET {api_prefix}/threads`: List threads accessible to the user.
    - `GET {api_prefix}/threads/{thread_id}/history`: Fetch thread message history and workspace state.
    - `GET {api_prefix}/threads/{thread_id}/visualizations`: Fetch pinned visualizations for a thread.
    - `PUT {api_prefix}/threads/{thread_id}` and `DELETE {api_prefix}/threads/{thread_id}`: Update or delete a thread.
    - `GET/POST {api_prefix}/agents` and `PUT/DELETE {api_prefix}/agents/{agent_id}`: Manage agent definitions.
- The `get_history` API exposes `additional_kwargs` on messages to support extended capabilities like returning image URLs, MFE content, and Mermaid diagrams.
- Requests must include a verified `Authorization: Bearer <JWT>` header to authenticate the user via `sub` claim for multi-user state retrieval.

### 6.3 User Settings
- The service provides endpoints to manage per-user configuration:
    - `GET {api_prefix}/user/settings`: Retrieves the current settings for the authenticated user (e.g., `learning_mode_enabled`).
    - `PUT {api_prefix}/user/settings`: Updates the settings for the authenticated user.
- These settings are used as defaults for new threads and to control global agent behavior.

## 7. Development Guidelines

### 6.1 General
- Run tests using the provided Makefile targets (e.g., `make agent-be-test`).
- When modifying the agent flow, ensure that changes to graph construction occur at startup and do not introduce per-request overhead.
- Ensure new features or alterations to how the backend handles state are documented in this specification file.

### 6.2 Testing & Build Environment
- **Evaluation**: The backend uses `deepeval` for LLM-based evaluation of agent prompts and outputs.
- **Build Secrets**: Running tests during the Docker build process requires a valid `GOOGLE_API_KEY` passed as a Docker build secret (`--secret id=GOOGLE_API_KEY`). This key is used by the `GeminiJudge` in the evaluation suite.
- **CI/CD**: Ensure the CI environment (e.g., GitHub Actions) is configured to pass this secret during the build.
