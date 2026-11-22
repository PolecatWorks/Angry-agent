# Angry-Agent Specification System

This is the navigation hub for specifications, Product Requirements Documents (PRDs), TDD build specifications, and architecture documentation for the **Angry-Agent** application.

---

## Quick Navigation

### Product Requirements Documents (PRDs)
- **[PRDs Registry (`spec/prds/README.md`)](prds/README.md)** — Cross-container product and domain requirements:
  - [Bidirectional Shared Canvas & Live MFE Co-Editing PRD](prds/bidirectional-shared-canvas-mfe-prd.md)
  - [Autonomous Semantic Stewardship, Data Reasoning & Provenance Journey PRD](prds/semantic-steward-and-provenance-journey-prd.md)
  - [Backend-Specific Keycloak Claims, Service Accounts & Zero-Fake-Auth Architecture PRD](prds/service-claims-and-keycloak-auth-prd.md)

### TDD Build Specifications
- **[Build Specifications Index (`spec/specs/README.md`)](specs/README.md)** — Ordered TDD build specifications derived from PRDs (`draft` → `complete` → `deprecated`).

### System Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture overview, components, and data flows.

### Container Specifications
- **[Backend Container PRD (`agent-be-container/spec/prd.md`)](../agent-be-container/spec/prd.md)** — Rust backend (`Axum`, `Tokio`, `rig-core`, `sqlx`) API, SSE, tools, and persistence specifications.
- **[Frontend Container PRD (`agent-ui-container/spec/prd.md`)](../agent-ui-container/spec/prd.md)** — Angular Micro-Frontend (`Native Federation`, Angular Material) workspace and component specifications.

---

## Overview

The Angry-Agent application is a full-stack AI agent system divided into two independent Docker containers:

- **Frontend (`agent-ui-container`)** — Angular Micro-Frontend (MFE) with `@angular-architects/native-federation` and Angular Material.
- **Backend (`agent-be-container`)** — Rust backend powered by Axum, Tokio, `rig-core`, and `sqlx` (PostgreSQL).

---

## Specification Workflow

1. **Product Requirements (`spec/prds/`)** — Capture new domain capabilities, cross-container journeys, and API/UX contracts in focused PRDs and register them in [spec/prds/README.md](prds/README.md).
2. **TDD Build Specifications (`spec/specs/`)** — Derive ordered implementation and test specifications from PRDs and track their lifecycle (`draft` → `complete` → `deprecated`) in [spec/specs/README.md](specs/README.md).
3. **Container PRDs (`agent-be-container/spec/`, `agent-ui-container/spec/`)** — Keep container-level PRDs synchronized whenever container functionality, API contracts, or UI behavior changes.

---

## Container Guidelines

### Frontend Container (`agent-ui-container`)
- **Framework:** Angular with Angular Material
- **Module Federation:** `@angular-architects/native-federation` remote (`./routes` mapped to `remote.routes.ts`)
- **Package Manager:** `npm`
- **Testing:** `make agent-ui-test` (`ng test --watch=false` / Vitest)
- **Auth:** Currently mocked via headers (`X-User-ID`); see [Keycloak Auth PRD](prds/service-claims-and-keycloak-auth-prd.md) for production OIDC migration.

### Backend Container (`agent-be-container`)
- **Framework:** Rust with Axum and Tokio
- **AI Logic:** `rig-core` for agent logic and tools
- **Persistence:** `sqlx` (PostgreSQL) with startup migrations and in-memory active session stores
- **Dependency Manager:** Cargo
- **Testing:** `make agent-be-test`
- **Atomic Operations:** Verify access and constraints directly inside `UPDATE`/`DELETE` SQL statements (e.g., `WHERE id = $1 AND user_id = $2`) rather than read-then-write patterns.

**Important:** Keep containers independent (no Docker Compose). Communicate across containers via stable API contracts.

---

## Related Resources

- **[Project README](../README.md)**
- **[Repository Agent Guidelines](../AGENTS.md)**
- **[Getting Started Guide](../docs/GETTING_STARTED.md)**
- **[Frontend Container README](../agent-ui-container/README.md)**
- **[Backend Container README](../agent-be-container/README.md)**
