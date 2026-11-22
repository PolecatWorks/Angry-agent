# AI Agent Repository Guidelines

Welcome to the AI Agent application repository. This repository contains a full-stack AI agent application divided into two independent containers:
- `agent-ui-container`: An Angular Micro-Frontend (MFE) application.
- `agent-be-container`: A Rust Backend application powered by Axum, Tokio, rig-core, and sqlx.

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

## 4. Backend Guidelines (`agent-be-container` - Rust)

- **Framework:** Axum and Tokio.
- **Dependency Manager:** Cargo.
- **AI/Logic:** `rig-core` for agent logic and tools; `sqlx` (PostgreSQL) for persistence and checkpointing.
- **Execution Model:** Router, database connection pools, agent tools, and in-memory session/catalog stores are constructed at startup.
- **Atomic Operations:** When verifying access or constraints before modifying data, incorporate those criteria directly into the `UPDATE` or `DELETE` SQL statement (e.g., `WHERE id = $1 AND user_id = $2`). Avoid read-then-write anti-patterns to prevent race conditions.

## 5. General Development Principles

- **Testing:** Always ensure tests are passing (`make agent-be-test` / `make agent-ui-test`) before proposing a change. Attempt to write tests for new functionality.
- **Documentation:** Keep inline documentation and README files up to date.
- **Verification:** Always verify your work after modifying files by reading them back to ensure correctness.
- **Imports:** Prefer placing all imports at the top of the file rather than inside functions. This ensures missing or incorrect imports are caught when the module is parsed rather than during runtime execution.

## 6. Pre-commit Checks

Always perform the required pre-commit checks before submitting any changes. Verify functionality and ensure all tests pass.

## 7. Boot-Time Validation & Code Refinement Standards

- **Fail-Fast Boot Sequence**: Validate all CLI arguments, configuration files, secrets, database connectivity, and migrations **before** starting HaMS (`/hams/alive`, `/hams/ready`) or binding the HTTP listener: `Parse CLI -> Load & validate config -> Connect DB & run migrations -> Init domain stores/clients -> Start HaMS & mark ready -> Bind HTTP listener`.
- **No Config Defaults / No Soft-Fail**: Operational configuration fields must be explicitly defined and validated. Never use `#[serde(default)]` for required settings, and never fall back to a default value when validation or loading fails—treat it as a fatal boot error.
- **Minimize `Option<T>`**: Never use `Option<T>` for required runtime dependencies or CLI plumbing (e.g., `--config`, `--secrets`, DB pools, auth config). Use `Option<T>` only where absence is a valid domain state (e.g., optional query filters or lookup results).
- **Propagate Errors with `?` & Never Swallow Errors**: Use `thiserror` + `#[from]` and propagate via `?` instead of nested `match`/`if let` blocks. Translate errors only at system boundaries (`IntoResponse`). Never discard fallible results via `let _ = ...`, `.ok()`, or `.unwrap_or_default()` on DB/deserialization reads.
- **Parse, Don't Validate & Minimize Ambiguity**: Parse raw inputs into strong types (`Url`, `SocketAddr`, `Uuid`, domain enums) at the boundary; avoid stringly-typed flags, duplicate routes, or `200 OK` error payloads.

## 8. Build & Test Execution

- **Always Use `Makefile` Targets**: When running builds or tests, always use the `Makefile` rather than invoking `cargo`, `npm`, or `ng` directly. Run `make help` to see all available targets.
