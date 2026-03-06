# AI Agent Repository Guidelines

Welcome to the AI Agent application repository. This repository contains a full-stack AI agent application divided into two independent containers:
- `agent-ui-container`: An Angular Micro-Frontend (MFE) application.
- `agent-be-container`: A Python Backend application powered by Aiohttp and LangGraph.

When working within this repository as an automated agent, please follow the guidelines outlined below to ensure consistency, reliability, and maintainability of the codebase.

## 1. Specification Files (PRD) Maintenance

**CRITICAL:** The specification documents located in `agent-ui-container/spec/` and `agent-be-container/spec/` must be kept up to date at all times.

- Whenever a new feature is added, an existing feature is modified, or the application's functionality is changed, you **must** update the corresponding Product Requirements Document (PRD) in the respective `spec` directory.
- The PRDs act as the source of truth for the design, objectives, and functionality of each container.
- If you refactor code or change how the frontend communicates with the backend, ensure these changes are accurately reflected in the specifications.

## 2. Container Independence

- The frontend (`agent-ui-container`) and backend (`agent-be-container`) are designed to run as independent Docker containers.
- **Do not use Docker Compose.** The user explicitly prohibits its use to facilitate future migration to Kubernetes.
- Changes in one container should be isolated as much as possible, relying on stable API contracts to communicate.

## 3. Frontend Guidelines (`agent-ui-container`)

- **Framework:** Angular and Angular Material.
- **Package Manager:** `npm`.
- **Architecture:** The application is configured as a Module Federation remote using `@angular-architects/native-federation`.
- **Routing:** Exposes functionality via route configurations (`./routes`) mapped to `remote.routes.ts` for internal navigation when embedded.
- **Testing:** Frontend tests are executed using `ng test --watch=false` (integrated with Vitest).
- **Authentication:** Currently mocked via headers (e.g., `X-User-ID`). *Note: Future plans involve migrating to OAuth2.*

## 4. Backend Guidelines (`agent-be-container`)

- **Framework:** Aiohttp.
- **Dependency Manager:** Poetry.
- **AI/Logic:** LangGraph for agent logic backed by PostgreSQL for state/history persistent checkpointing.
- **LLM:** Currently uses `langchain-google-genai` (configurable).
- **Execution Model:** LangGraph models and graphs **must be constructed on application startup** (e.g., via a handler class) and executed on API calls. Do not construct the graph per request.
- **System Prompts:** Configurable via `ServiceConfig` and passed to the agent handler at startup.

## 5. General Development Principles

- **Testing:** Always ensure tests are passing (`make agent-be-test` / `ng test --watch=false`) before proposing a change. Attempt to write tests for new functionality.
- **Documentation:** Inline documentation, especially for Python, is highly encouraged. Keep the README files up to date.
- **Verification:** Always verify your work after modifying files by reading them back to ensure correctness.

## 6. Pre-commit Checks

Always perform the required pre-commit checks before submitting any changes. Verify functionality and ensure all tests pass.
