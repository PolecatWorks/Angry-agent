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
- LangGraph integrates directly with a PostgreSQL backend to manage check-pointing. Chat history and current agent state are preserved across requests based on the user's session identifier.

### 4.4 Intent Routing Logic & Post-Processing
The backend includes specific routing and post-processing mechanisms for processing messages.
- **Intent Routing**: Messages containing simple greetings (like 'hello') can be intercepted and handled directly. Specific keywords (e.g., 'draw', 'picture', 'image') are routed to an `image_node`.
- **MFE Tool Support**: The agent has access to tools that can generate data for Micro-Frontend (MFE) components (like Markdown, JSON, Charts, or Mermaid diagrams).
- **Packager Node**: A dedicated node (the "Packager") runs after the LLM/Tool loop to convert the conversation into a sequence of MFEContent objects.
    - **Packaging**: It consolidates helpful AI text and ToolMessage results into a list of MFEs.
    - **Finalization**: It marks the final AIMessage with `packaged: True` in `additional_kwargs` to signal completion to the frontend.
    - **Tool-Call Fallback**: It is responsible for detecting "lost" tool call attempts (where the LLM placed JSON in the message content instead of tool-calling metadata). It manually executes these tools and injects the results into the packager's view to ensure a consistent UI representation.
- **MFE Tools**:
    - `generate_mfe_of_markdown`: For rendering markdown text via `MarkdownShowWrapper`.
    - `generate_mfe_of_text`: For rendering plain text via `TextShowWrapper`.
    - `generate_mfe_of_json`: For general JSON/structured data via `JsonShowWrapper`.
    - `generate_data_visualization`: For D3-based graphs via `DataShowWrapper`.
    - `generate_mfe_of_mermaid` and `visualize_graph`: For Mermaid diagrams via `MermaidShowWrapper`.

## 5. API Interface Expectations
- Specific keywords (e.g., 'draw', 'picture', 'image') are intercepted and routed to an `image_node` which currently returns a placeholder image via `additional_kwargs`.

## 6. API Interface Expectations
- The service exposes endpoints for the frontend to submit messages and fetch chat history. The `get_history` API exposes `additional_kwargs` on messages to support extended capabilities like returning image URLs.

- The service exposes endpoints for the frontend to submit messages and fetch chat history.
- The structure of requests should consistently provide the necessary authentication headers (`X-User-ID`) to allow proper multi-user state retrieval.

## 6. Development Guidelines

### 6.1 General
- Run tests using the provided Makefile targets (e.g., `make agent-be-test`).
- When modifying the agent flow, ensure that changes to graph construction occur at startup and do not introduce per-request overhead.
- Ensure new features or alterations to how the backend handles state are documented in this specification file.

### 6.2 Testing & Build Environment
- **Evaluation**: The backend uses `deepeval` for LLM-based evaluation of agent prompts and outputs.
- **Build Secrets**: Running tests during the Docker build process requires a valid `GOOGLE_API_KEY` passed as a Docker build secret (`--secret id=GOOGLE_API_KEY`). This key is used by the `GeminiJudge` in the evaluation suite.
- **CI/CD**: Ensure the CI environment (e.g., GitHub Actions) is configured to pass this secret during the build.
