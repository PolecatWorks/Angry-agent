# AI Agent Chat & Form Canvas Application

This project consists of an Angular Frontend and alternative Python and Rust Backends, designed to run as independent Docker containers.

## Project Structure
- `agent-ui-container/`: Angular Application (Module Federation Remote / Host Shell)
- `agent-be-container/`: High-performance Rust Backend (Tokio, Axum, rig-core, AG-UI protocol over SSE, RFC 6902 JSON Patch state delta handling, inspired by `agent-as-data` and `Graphrag`)
- `agentpy-be-container/`: Python Backend (Poetry, Aiohttp, LangGraph, PostgreSQL)

> 📖 **New to the app? Check out the [Getting Started Tutorial](docs/GETTING_STARTED.md)** for a guided walkthrough of the split-pane workspace and live co-editing canvas.

## Running the Application

### Prerequisites
- Docker

### 1. Database (PostgreSQL)
Run the following command to start a PostgreSQL container:

```bash
make db-local
```

### 2. Backend

#### Option A: Rust Backend (agent-be-container)
Run the Rust backend locally or via Cargo/Docker:

```bash
# Run locally
make agent-be-dev

# Run tests
make agent-be-test

# Build/run container
make agent-be-docker-run
```

#### Option B: Python Backend (agentpy-be-container)
Build and run the Python backend container:

```bash
make agentpy-be-docker-run
```

### 3. Frontend
Build and run the frontend container.

**Run:**
```bash
make agent-ui-docker-run
```

Access the application at `http://localhost:4200`.

## Features
- **Multi-User Isolation**: Chats are isolated by User ID (Mocked via Login screen).
- **Persistent History**: Chat history is stored in PostgreSQL.
- **LangGraph Agent**: Uses LangGraph with Postgres Checkpointing.
- **Interactive Workspace**: A dynamic panel for pinning, editing, and reordering visualizations (Charts, JSON, Mermaid diagrams) using a BREAD (Browse, Read, Edit, Add, Delete) toolset.
- **Bidirectional Agentic Form Canvas (`agentrs-be`)**:
  - Real-time split-pane collaboration between direct human form inputs (RHS) and conversational agent actuation (LHS).
  - Server-Sent Events (SSE) compliant with AG-UI v1.0 protocol.
  - RFC 6902 JSON Patch state deltas (`STATE_DELTA`) with conflict prevention for user-focused fields.
  - Dynamic schema-driven tools for form mutation, hot-swapping forms (`switch_active_form`), and human-in-the-loop submission approvals (`request_form_submission`).
  - Sample test forms provided under `agentrs-be-container/tests/sample_forms/` (`vendor_onboarding_v2.json`, `expense_claim_v1.json`).

## Data Persistence Architecture

The application uses PostgreSQL to store two different scopes of data: Application Metadata and LangGraph State (which includes chat messages).

```mermaid
erDiagram
    %% Application metadata
    THREADS {
        string thread_id PK
        string user_id "Owner of the thread"
        string title "Thread display name"
        string color "UI color theme"
        string status_msg "Current agent status"
        timestamp status_updated_at
        timestamp locked_until "Concurrency lock"
        timestamp created_at
        timestamp updated_at
    }

    %% Managed entirely by LangGraph Checkpointer
    CHECKPOINTS {
        string thread_id PK, FK
        string checkpoint_ns PK
        string checkpoint_id PK "State version ID"
        string parent_checkpoint_id
        jsonb type
        jsonb checkpoint
        bytea metadata
    }

    CHECKPOINT_BLOBS {
        string thread_id PK, FK
        string checkpoint_ns PK
        string channel PK
        string version PK
        string type
        bytea blob "Serialized channel data (e.g. Chat Messages)"
    }

    CHECKPOINT_WRITES {
        string thread_id PK, FK
        string checkpoint_ns PK
        string checkpoint_id PK, FK
        string task_id PK
        string idx PK
        string channel
        string type
        bytea blob "Pending task writes"
    }

    THREADS ||--o{ CHECKPOINTS : "contains state history"
    CHECKPOINTS ||--o{ CHECKPOINT_BLOBS : "stores large state channels"
    CHECKPOINTS ||--o{ CHECKPOINT_WRITES : "stores pending writes"
```

### 1. Application Metadata (`threads` table)
Managed natively by the backend application (see `agent-be-container/migrations/001_initial_schema.sql`).
It tracks the *existence* and UI-level metadata of a chat session.
- **`thread_id`**: The unique identifier for a chat. Used by LangGraph as the thread identifier.
- **`user_id`**: Associates the thread with a specific user for isolation.
- **Core Data**: Title, UI color theme, current agent running status messages, and concurrency locks (`locked_until`).

### 2. Agent State & Messages (`checkpoints_*` tables)
Managed automatically by LangGraph's internal `AsyncPostgresSaver`.
It persists the *State* of the AI agent at each node transition, including the entire conversation history.
- **`checkpoints`**: Stores the metadata and version controlling of the graph state at each step.
- **`checkpoint_blobs`**: Stores the actual serialized state channels. **This is where the actual Chat Messages are physically stored** as serialized binary blobs, linked directly to the `thread_id`.
- **`checkpoint_writes`**: Used by LangGraph for internal task management and pending state writes during complex graph executions.

## Development (Local)

**Backend:**
```bash
# Ensure Postgres is running on localhost:5432
make agent-be-dev
```

**Frontend:**
```bash
make agent-ui-dev
```

## GitHub Actions & Continuous Deployment

This repository uses GitHub Actions to build and publish Docker images when code is merged to `main`.

A deployment workflow (`update-fluxcd.yml`) automatically updates the image tags in the `fluxcd-dev/` directory to deploy the new images. In order to bypass branch protections and commit directly to the `main` branch, it requires a Personal Access Token (PAT).

### Setting up the PAT Secret
1. Create a Personal Access Token (PAT) in GitHub:
   - **Classic Token:** Requires the `repo` scope.
   - **Fine-grained Token (Recommended):** Requires `Contents: Read and write` repository permissions.
2. Go to your repository settings on GitHub.
3. Navigate to **Secrets and variables > Actions**.
4. Create a new repository secret named `PAT` and paste the token value.
