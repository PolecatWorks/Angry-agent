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
docker run --name agent-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=agentdb \
  -p 5432:5432 \
  -d postgres:15-alpine
```

### 2. Backend
Build and run the backend container. It needs to connect to the Postgres database.
If running on the same host (Mac/Windows), you can use `host.docker.internal` to access the postgres port mapped to localhost.

**Build:**
```bash
cd agent-be-container
docker build -t agent-be .
```

**Run:**
```bash
docker run --name agent-be \
  -p 8000:8000 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=agentdb \
  agent-be
```
*Note: On Linux, add `--add-host=host.docker.internal:host-gateway` to the run command, or use a shared docker network.*

### 3. Frontend
Build and run the frontend container.

**Build:**
```bash
cd agent-ui-container
docker build -t agent-ui .
```

**Run:**
```bash
docker run --name agent-ui \
  -p 80:80 \
  agent-ui
```

Access the application at `http://localhost`.

## Features
- **Multi-User Isolation**: Chats are isolated by User ID (Mocked via Login screen).
- **Persistent History**: Chat history is stored in PostgreSQL.
- **LangGraph Agent**: Uses LangGraph with Postgres Checkpointing.

## Development (Local)

**Backend:**
```bash
cd agent-be-container
poetry install
# Ensure Postgres is running on localhost:5432
python src/main.py
```

**Frontend:**
```bash
cd agent-ui-container
npm install
npm start
```
