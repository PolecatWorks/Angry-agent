# AI Agent Chat Application

This project consists of an Angular Frontend and a Python Backend (using LangGraph), designed to run as independent Docker containers.

## Project Structure
- `agent-ui-container/`: Angular Application
- `agent-be-container/`: Python Backend (Poetry, Aiohttp, LangGraph)

## Running the Application

### Prerequisites
- Docker

### 1. Database (PostgreSQL)
Run the following command to start a PostgreSQL container:

```bash
make db-local
```

### 2. Backend
Build and run the backend container. It needs to connect to the Postgres database.

**Run:**
```bash
make agent-be-docker-run
```
*Note: This target handles building the image and setting up environment variables.*

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
