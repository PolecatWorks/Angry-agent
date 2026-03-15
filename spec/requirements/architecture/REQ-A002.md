# REQ-A002: Backend Container Architecture

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Establish the backend container architecture for the Angry-Agent application using Aiohttp with LangGraph AI logic. Define the structural foundation, API design, agent execution model, state management, and database integration for the Python-based backend service.

---

## Rationale

The backend needs a scalable, async-first architecture that:
- Handles concurrent API requests efficiently with Aiohttp
- Executes LangGraph agent logic with persistent state checkpointing
- Integrates with LLM providers (Google GenAI, configurable)
- Manages PostgreSQL connections for state persistence
- Supports atomic database operations without race conditions
- Enables easy configuration for different environments

---

## Key Implementation Points

1. **Aiohttp Server Setup** — Configure async web server with proper middleware
2. **LangGraph Integration** — Construct graphs at startup, not per-request
3. **State Persistence** — Use PostgreSQL checkpoints for agent state recovery
4. **Atomic Operations** — Use WHERE clauses in UPDATE/DELETE, not SELECT-then-write
5. **API Layer** — Define REST endpoints with clear contracts (documented via OpenAPI)
6. **Error Handling** — Consistent error responses with proper HTTP status codes
7. **Environment Configuration** — Support dev, test, prod configurations
8. **Logging & Observability** — Structured logging for debugging and monitoring

---

## Current Status

💡 **PROPOSED** — Backend architecture ready to be implemented following Aiohttp + LangGraph patterns.

---

## Work Items

### 🟠 WORK-A002-001: Configure Aiohttp Server

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 4-6 hours  
**Description:** Set up and configure Aiohttp web server with middleware, routing, and request handling

**Problem:**
- No formal server configuration
- Routing and middleware setup unclear
- Request/response handling not documented

**Solution:**
- Create Aiohttp application factory
- Configure middleware stack (logging, CORS, error handling)
- Set up API route structure
- Document request/response flow

**Files to Change:**
- `agent-be-container/main.py`
- `agent-be-container/app/server.py` (create if missing)
- `agent-be-container/app/middleware/` (create if missing)

**Acceptance Criteria:**
- [ ] Aiohttp server starts and listens on configured port
- [ ] Middleware stack properly configured
- [ ] Routes organized by feature/domain
- [ ] Error handling returns consistent responses
- [ ] Logging captures all requests

**Related Issues:** [GAP_ANALYSIS.md Issue #5 (Deployment)](../../GAP_ANALYSIS.md)

**Dependencies:** None

---

### 🟠 WORK-A002-002: Integrate LangGraph Agent

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 5-7 hours  
**Description:** Set up LangGraph graph construction and execution at server startup

**Problem:**
- No LangGraph integration
- Agent execution model undefined
- Graph construction timing unclear

**Solution:**
- Create graph factory that builds at startup
- Define agent nodes and edges
- Implement graph execution handler
- Handle agent state and outputs

**Files to Change:**
- `agent-be-container/app/agent/` (create if missing)
- `agent-be-container/app/agent/graph.py`
- `agent-be-container/app/agent/handler.py`

**Acceptance Criteria:**
- [ ] Graph constructs successfully at server startup
- [ ] Agent receives user input and generates responses
- [ ] State transitions work correctly
- [ ] LLM integration working
- [ ] Handles errors gracefully

**Related Issues:** [GAP_ANALYSIS.md Issue #6 (Agent Workflow)](../../GAP_ANALYSIS.md)

**Dependencies:** WORK-A002-001 (server setup)

---

### 🟠 WORK-A002-003: Configure PostgreSQL Checkpointing

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-5 hours  
**Description:** Set up PostgreSQL connection pool and LangGraph checkpoint storage

**Problem:**
- PostgreSQL schema not documented
- Checkpoint storage not configured
- Connection pooling not set up

**Solution:**
- Create connection pool configuration
- Set up LangGraph PostgreSQL checkpoint store
- Document schema and migrations
- Handle connection lifecycle

**Files to Change:**
- `agent-be-container/app/database/` (create if missing)
- `agent-be-container/app/database/connection.py`
- `agent-be-container/migrations/` (create if missing)

**Acceptance Criteria:**
- [ ] PostgreSQL connection pool working
- [ ] Checkpoints stored correctly
- [ ] State recovery working across restarts
- [ ] Schema documented
- [ ] Migrations automated

**Related Issues:** [GAP_ANALYSIS.md Issue #2 (Database Schema)](../../GAP_ANALYSIS.md)

**Dependencies:** None

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A001: Frontend Container Architecture](../architecture/REQ-A001.md) — Communicates with this backend
- [REQ-A003: Authentication & Authorization](../architecture/REQ-A003.md) — Security layer for backend
- [REQ-F007: Core API Endpoints](../features/REQ-F007.md) — API contract exposed by this backend
- [REQ-D009: Database Schema Documentation](../documentation/REQ-D009.md) — Database implementation details

---

## Notes

### Backend Technology Stack (Current)
- **Framework:** Aiohttp
- **AI/Agent:** LangGraph with langchain
- **LLM Provider:** langchain-google-genai (configurable)
- **Database:** PostgreSQL for state persistence
- **Language:** Python 3.11+
- **Dependency Manager:** Poetry
- **Testing:** pytest

### Key Design Principles
- **Async-First:** All I/O operations are async (Aiohttp + asyncio)
- **Stateful Agent:** LangGraph maintains conversation state via checkpoints
- **Atomic Operations:** Database writes use WHERE clauses to prevent race conditions
- **Configuration Driven:** Environment variables for all settings
- **Single Graph Instance:** Graph constructed once at startup, reused for all requests

### Future Considerations
- Message queue for async task processing
- Caching layer for frequently accessed data
- Multi-region deployment support
- Advanced monitoring and tracing
- GraphQL API alongside REST

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
