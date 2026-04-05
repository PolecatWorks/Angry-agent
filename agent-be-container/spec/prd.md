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
- Authentication currently relies on a mocked header (e.g., `X-User-ID`), but the architecture supports future integration with standard OAuth2 flows.
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
    - **Extraction**: It scans all messages in the current turn (AIMessages and ToolMessages) to extract `MFEContent` and Mermaid diagrams. This allows tools to return structured data that is automatically bubbled up to the UI metadata.
    - **Metadata Injection**: It populates `mfe_contents` and `mermaid_diagrams` in the final AIMessage's `additional_kwargs`. 
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

## 6. API Interface Expectations
### 6.1 Chat & Threads
- The service exposes endpoints for the frontend to submit messages (`/api/chat`), list threads (`/api/threads`), and fetch thread history (`/api/threads/{thread_id}/history`).
- The `get_history` API exposes `additional_kwargs` on messages to support extended capabilities like returning image URLs, MFE content, and Mermaid diagrams.
- Requests must include the necessary authentication headers (`X-User-ID`) to allow proper multi-user state retrieval.

### 6.2 User Settings
- The service provides endpoints to manage per-user configuration:
    - `GET /api/user/settings`: Retrieves the current settings for the authenticated user (e.g., `learning_mode_enabled`).
    - `PUT /api/user/settings`: Updates the settings for the authenticated user.
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
