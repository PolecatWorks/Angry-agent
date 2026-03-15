# Angry-Agent System Architecture

**Document Status:** ACTIVE  
**Version:** 1.0  
**Date:** 2026-03-15

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [System Components](#system-components)
3. [Key Technologies](#key-technologies)
4. [Data Flow](#data-flow)
5. [Deployment Architecture](#deployment-architecture)
6. [Architecture Decisions](#architecture-decisions)

---

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Angry-Agent Application                  │
├──────────────────────────────────┬──────────────────────────┤
│                                  │                          │
│   FRONTEND CONTAINER             │   BACKEND CONTAINER     │
│   (agent-ui-container)           │   (agent-be-container)  │
│                                  │                         │
│   ┌──────────────────┐          │   ┌─────────────────┐   │
│   │  Angular MFE     │          │   │  Aiohttp Server │   │
│   │  (Port 4200)     │─────────────→│  (Port 8000)    │   │
│   │                  │          │   │                 │   │
│   │  • Routing       │          │   │ • API Endpoints │   │
│   │  • Components    │          │   │ • LangGraph     │   │
│   │  • Material UI   │          │   │ • Agent Logic   │   │
│   └──────────────────┘          │   │ • State Mgmt    │   │
│                                  │   └────────┬────────┘   │
└──────────────────────────────────┼────────────┼────────────┘
                                   │   ┌────────▼────────┐
                                   │   │  PostgreSQL DB  │
                                   │   │ (Checkpointing) │
                                   │   └─────────────────┘
                                   │
                                   │   ┌─────────────────┐
                                   │   │ LLM Provider    │
                                   └──→│ (Google GenAI)  │
                                       └─────────────────┘
```

**Key Characteristics:**
- **Containerized:** Each component runs in its own Docker container
- **Stateless Frontend:** Angular MFE communicates via HTTP REST/GraphQL API
- **Stateful Backend:** Maintains session state via LangGraph checkpoints in PostgreSQL
- **Independent Containers:** Frontend and backend can scale separately
- **Future-Ready:** Designed for Kubernetes deployment (no Docker Compose)

---

## System Components

### Component 1: Frontend (Angular Micro-Frontend)

```
┌─────────────────────────────────┐
│   Angular Application           │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────────┐│
│  │  Native Federation (MFE)    ││
│  │  • Route-based remotes      ││
│  │  • Shared dependencies      ││
│  └────────────┬────────────────┘│
│               │                 │
│  ┌────────────▼────────────────┐│
│  │  Feature Modules             ││
│  │  • Dashboard                 ││
│  │  • Agent Interactions        ││
│  │  • Settings                  ││
│  └─────────────────────────────┘│
│               │                 │
│  ┌────────────▼────────────────┐│
│  │  Angular Material            ││
│  │  • UI Components             ││
│  │  • Responsive Design         ││
│  └─────────────────────────────┘│
│               │                 │
│  ┌────────────▼────────────────┐│
│  │  HTTP Client (API Layer)     ││
│  │  • REST/GraphQL Calls        ││
│  │  • Header Auth (X-User-ID)   ││
│  └──────────────────────────────┘
└─────────────────────────────────┘
         ↓
    Backend API
```

**Responsibilities:**
- Render user interface using Angular components
- Handle client-side routing via Native Federation
- Manage user interactions and form inputs
- Make API calls to backend services
- Display agent responses and interaction history

**Location:** `/agent-ui-container/`

**Key Technologies:** Angular, Angular Material, Native Federation, TypeScript, RxJS

---

### Component 2: Backend (Aiohttp + LangGraph)

```
┌──────────────────────────────────┐
│   Aiohttp Application            │
│   (Python Async Web Server)      │
├──────────────────────────────────┤
│                                  │
│  ┌──────────────────────────────┐│
│  │  API Layer                   ││
│  │  • REST Endpoints            ││
│  │  • Request/Response Handling  ││
│  │  • Authentication/Validation  ││
│  └────────────┬─────────────────┘│
│               │                  │
│  ┌────────────▼─────────────────┐│
│  │  LangGraph Agent             ││
│  │  • Graph Construction        ││
│  │  • Agent State Management    ││
│  │  • Tool Execution           ││
│  └────────────┬─────────────────┘│
│               │                  │
│  ┌────────────▼─────────────────┐│
│  │  LLM Integration             ││
│  │  • Provider: Google GenAI    ││
│  │  • Prompt Management         ││
│  │  • Token Handling            ││
│  └────────────┬─────────────────┘│
│               │                  │
│  ┌────────────▼─────────────────┐│
│  │  State Checkpointing         ││
│  │  • PostgreSQL Backend        ││
│  │  • Session Persistence       ││
│  │  • History Tracking          ││
│  └──────────────────────────────┘
└──────────────────────────────────┘
```

**Responsibilities:**
- Expose REST/GraphQL API for frontend consumption
- Execute LangGraph agent logic
- Manage conversation state and history
- Interact with LLM providers
- Persist state to PostgreSQL

**Location:** `/agent-be-container/`

**Key Technologies:** Aiohttp, LangGraph, PostgreSQL, langchain-google-genai, Python 3.11+

---

### Component 3: Data Storage (PostgreSQL)

**Responsibilities:**
- Store LangGraph checkpoints for state persistence
- Maintain conversation history
- Track user sessions
- Support transaction consistency

**Configuration:** Configurable connection string, supports local and managed instances

---

## Key Technologies

### Frontend Stack
- **Framework:** Angular 18+
- **UI Library:** Angular Material
- **Module Federation:** @angular-architects/native-federation
- **Language:** TypeScript
- **Testing:** Vitest (via ng test)
- **Package Manager:** npm
- **Auth:** Header-based (X-User-ID) — *Future: OAuth2*

### Backend Stack
- **Framework:** Aiohttp
- **AI/Agent:** LangGraph with langchain ecosystem
- **LLM Provider:** langchain-google-genai (configurable)
- **Database:** PostgreSQL (state checkpointing)
- **Language:** Python 3.11+
- **Dependency Manager:** Poetry
- **Testing:** pytest
- **Auth:** Header-based validation — *Future: OAuth2*

### Infrastructure Stack
- **Container Runtime:** Docker
- **Orchestration:** Kubernetes (planned) — *Note: No Docker Compose per requirements*
- **Version Control:** Git
- **CI/CD:** GitHub Actions

---

## Data Flow

### User Request → Agent Response Flow

```
User Browser                 Frontend Container         Backend Container
┌──────────────┐            ┌────────────────┐        ┌──────────────────┐
│              │            │                │        │                  │
│  1. User     │            │                │        │                  │
│  interacts   │            │                │        │                  │
│  with UI     │            │                │        │                  │
└────────┬─────┘            └────────────────┘        └──────────────────┘
         │
         │  2. HTTP Request (POST /api/chat)
         ├───────────────────────────────────────────→
         │                   │
         │                   │  3. Parse request
         │                   │  4. Validate headers
         │                   ├──────────────────────→
         │                   │                   │
         │                   │                   │  5. Load session state
         │                   │                   │     from checkpoint
         │                   │                   ├──→ [PostgreSQL]
         │                   │                   │
         │                   │                   │  6. Construct/Execute
         │                   │                   │     LangGraph nodes
         │                   │                   │
         │                   │                   │  7. Call LLM
         │                   │                   ├──→ [Google GenAI]
         │                   │                   │
         │                   │                   │  8. Update state
         │                   │                   │     checkpoint
         │                   │                   ├──→ [PostgreSQL]
         │                   │
         │                   │  9. JSON Response
         │  ← ────────────────────────────────────
         │                   │
         │  10. Update UI
         │      Display
         │      response
```

**Detailed Steps:**
1. User types message or clicks action in Angular UI
2. Frontend creates HTTP request with X-User-ID header
3. Aiohttp server receives request on /api/chat endpoint
4. Backend validates authentication via header
5. Loads LangGraph state checkpoint from PostgreSQL
6. Executes graph nodes with user input
7. Interacts with LLM provider for response generation
8. Saves updated state back to PostgreSQL checkpoint
9. Returns JSON response to frontend
10. Frontend updates UI with agent response

---

## Deployment Architecture

### Development Environment

```
Developer Machine
┌────────────────────────────────────┐
│  Docker Desktop                    │
├────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────┐ │
│  │ Frontend     │  │  Backend   │ │
│  │ localhost    │  │  localhost │ │
│  │ :4200        │  │  :8000     │ │
│  └──────────────┘  └────────────┘ │
│         ↓                  ↓       │
│         └──────┬───────────┘       │
│                │                  │
│         ┌──────▼────────┐         │
│         │  PostgreSQL   │         │
│         │  localhost    │         │
│         │  :5432        │         │
│         └───────────────┘         │
└────────────────────────────────────┘
```

**Setup:** Each container runs independently. Frontend accessible on :4200, backend on :8000.

### Production Environment (Future Kubernetes)

```
Kubernetes Cluster
┌──────────────────────────────────────────────┐
│  Ingress / Load Balancer                     │
└────────────┬─────────────────────────────────┘
             │
    ┌────────┴─────────┐
    │                  │
┌───▼──────┐    ┌─────▼────┐
│ Frontend  │    │  Backend  │
│ Pod       │    │  Pod      │
│ Replicas  │    │  Replicas │
│ :4200     │    │  :8000    │
└───┬──────┘    └─────┬────┘
    │                 │
    │                 │
    │          ┌──────▼────────┐
    │          │  PostgreSQL   │
    │          │  StatefulSet  │
    │          │  Persistent   │
    │          │  Volume       │
    │          └───────────────┘
    │
    └──→ [External LLM API]
         (Google GenAI, etc.)
```

**Key Points:**
- Frontend and backend scale independently
- PostgreSQL as StatefulSet for persistence
- External LLM API calls handled by backend
- No Docker Compose — direct Kubernetes manifests

---

## Architecture Decisions

### Decision 1: Containerized Microservices

**Decision:** Deploy frontend and backend as separate Docker containers instead of monolithic deployment.

**Rationale:**
- Enables independent scaling
- Allows separate technology stacks (Angular vs Python)
- Facilitates Kubernetes migration
- Supports team specialization (frontend vs backend engineers)

**Trade-offs:**
- Added complexity in API contracts
- Requires careful version management
- Need for cross-container communication

**Alternatives Considered:**
- Monolithic application (rejected: less flexible, hard to scale separately)
- Serverless functions (rejected: stateful agent requires persistent containers)
- Microservices with message queues (rejected: overkill for current scale)

---

### Decision 2: Native Federation for Module Federation

**Decision:** Use Angular's Native Federation instead of Module Federation plugins.

**Rationale:**
- Built-in Angular support, simpler setup
- Better TypeScript integration
- Reduces dependency on third-party plugins
- Improved bundling and performance

**Trade-offs:**
- Newer technology, smaller ecosystem
- Requires Angular 18+
- Less third-party tooling available

**Alternatives Considered:**
- Webpack Module Federation (rejected: older, more complex)
- Monolithic single Angular app (rejected: less modular, harder to maintain)

---

### Decision 3: LangGraph with PostgreSQL Checkpoints

**Decision:** Use LangGraph for agent logic with PostgreSQL for state persistence.

**Rationale:**
- LangGraph provides visual debugging and state management
- PostgreSQL checkpoints enable session persistence
- Enables replay and audit capabilities
- Built-in support for complex agent workflows
- Good integration with LangChain ecosystem

**Trade-offs:**
- PostgreSQL required (no in-memory storage)
- Graph construction overhead at startup
- Requires understanding of LangGraph paradigm

**Alternatives Considered:**
- In-memory state (rejected: no persistence across restarts)
- Redis-based checkpointing (rejected: less robust than PostgreSQL)
- Simple chat loop (rejected: insufficient for complex agents)

---

### Decision 4: Header-Based Authentication (Current)

**Decision:** Use HTTP headers (X-User-ID) for authentication during development.

**Rationale:**
- Simple to implement and test
- Fast development iteration
- No external auth infrastructure needed
- Easy to mock for unit tests

**Trade-offs:**
- Not production-safe
- Headers easily spoofed
- No encryption or signatures
- Manual header passing in API calls

**Planned Migration:**
- OAuth2 integration
- JWT token validation
- Secure session management

**Alternatives Considered:**
- API keys (rejected: no user tracking)
- JWT tokens now (rejected: adds complexity during development)
- Session cookies (rejected: cross-origin CORS complexity)

---

## Scaling Considerations

### Horizontal Scaling
- **Frontend:** Multiple Pod replicas behind load balancer
- **Backend:** Multiple Pod replicas sharing PostgreSQL checkpoint store
- **Database:** PostgreSQL replicas with read-only standby (future)

### Vertical Scaling
- Increase resource requests/limits on Pods
- Upgrade PostgreSQL hardware
- Optimize LLM API calls and caching

### Performance Bottlenecks
- **LLM API latency:** Mitigate with response caching and streaming
- **Database transactions:** Monitor checkpoint write throughput
- **Network latency:** Consider regional deployment
- **Token limits:** Implement message history pagination

### Mitigation Strategies
- Implement response caching layer
- Use connection pooling for PostgreSQL
- Add request queuing and backpressure
- Monitor metrics with Prometheus/Grafana
- Implement rate limiting at API gateway

---

## Known Limitations & Future Work

### Current Limitations
- Header-based authentication not production-ready
- Single PostgreSQL instance (no HA)
- LLM provider hardcoded to Google GenAI (though configurable)
- No multi-region support
- No message queue for async processing

### Planned Future Work
- OAuth2 authentication implementation
- Multi-region Kubernetes clusters
- Message queue for async agent tasks
- Comprehensive monitoring and observability
- API rate limiting and usage tracking
- Support for multiple LLM providers
- Advanced caching strategies
- Session persistence across deployments

---

## Related Requirements

For specifications related to this architecture:

- [REQ-A001: Frontend Container Architecture](requirements/architecture/REQ-A001.md)
- [REQ-A002: Backend Container Architecture](requirements/architecture/REQ-A002.md)
- [REQ-A003: Authentication & Authorization](requirements/architecture/REQ-A003.md)
- [REQ-F007: Core API Endpoints](requirements/features/REQ-F007.md)

See `requirements/README.md` for complete list.

---

**For questions or updates:** See GAP_ANALYSIS.md for known issues, or open a requirement in requirements/ directory.
