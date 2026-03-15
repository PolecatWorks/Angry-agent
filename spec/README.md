# Angry-Agent Specification System

**Last Updated:** 2026-03-15  
**System Status:** ACTIVE

This is the navigation hub for the RFC-inspired specification system for the Angry-Agent application. All requirements, architecture decisions, and documentation analysis are tracked here.

---

## Quick Navigation

### 📋 Requirements
- **[Requirements Index](requirements/README.md)** — Master index of all 17+ requirements
- **[Architecture Requirements](requirements/architecture/)** — Infrastructure, patterns, system design (REQ-A###)
- **[Feature Requirements](requirements/features/)** — Functionality, capabilities, integrations (REQ-F###)
- **[Documentation Requirements](requirements/documentation/)** — Guides, specifications, docs (REQ-D###)

### 🏗️ Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture overview, components, data flow
- **[GAP_ANALYSIS.md](GAP_ANALYSIS.md)** — Identified gaps and discrepancies across areas

---

## Overview

The Angry-Agent application is a full-stack AI agent system divided into two independent containers:

- **Frontend** (`agent-ui-container`) — Angular Micro-Frontend (MFE) with Native Federation
- **Backend** (`agent-be-container`) — Python/Aiohttp backend with LangGraph AI logic

This specification system ensures:
- ✅ All requirements are documented and tracked
- ✅ Architecture decisions are recorded with rationale
- ✅ Changes are coordinated between components
- ✅ Work is prioritized and dependencies are managed
- ✅ Issues and gaps are captured for resolution

---

## How to Use This System

### For Requirements Writers
1. Start with [Requirements Index](requirements/README.md)
2. Find the requirement you need to write
3. Use the template from the requirement category
4. Fill in all sections: Description, Rationale, Implementation Points
5. Link back to GAP_ANALYSIS.md if addressing an issue

### For Developers
1. Check [Requirements Index](requirements/README.md) for your work item
2. Read the full requirement file (e.g., REQ-A001.md)
3. Look at "Work Items" section for specific tasks
4. Update status as you progress
5. Document implementation results when complete

### For Architects
1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for current design
2. Check [Architecture Requirements](requirements/architecture/) for decisions
3. File issues in GAP_ANALYSIS.md if changes needed
4. Create/update REQ-A### files for architectural changes

### For QA/Testing
1. Check [GAP_ANALYSIS.md](GAP_ANALYSIS.md) for issues
2. Review related requirements to understand what needs testing
3. Verify acceptance criteria in work items are met
4. Report new issues back to GAP_ANALYSIS.md

---

## Requirement Categories

### Architecture (REQ-A###)
Infrastructure, system patterns, technology decisions, deployment architecture.

**Examples:** Native Federation setup, shared libraries, authentication patterns

### Features (REQ-F###)
Functional capabilities, integrations, user-facing functionality.

**Examples:** AI agent features, API endpoints, UI components

### Documentation (REQ-D###)
Guides, tutorials, specifications, internal documentation.

**Examples:** Setup guides, API documentation, architecture guides

---

## Key Principles

1. **Modular** — Each requirement is independent but can have dependencies
2. **Traceable** — Every change is linked to a requirement
3. **Versioned** — Requirements track versions and supersessions
4. **Atomic** — Work items in requirements are complete, testable units
5. **Integrated** — Architecture, requirements, and issues are connected

---

## Status Definitions

### Requirement Status
- **ACTIVE** — Currently implemented or in development
- **PROPOSED** — Planned for future implementation
- **SUPERSEDED** — Replaced by newer version (kept for audit trail)

### Work Item Status
- **✅ DONE** — Completed and verified
- **🔄 IN_PROGRESS** — Currently being worked on
- **⏳ PENDING** — Ready to start, waiting for resources
- **🚫 BLOCKED** — Cannot proceed, waiting for dependency

---

## Container Guidelines

### Frontend Container (`agent-ui-container`)
- **Framework:** Angular with Angular Material
- **Module Federation:** Native Federation remote
- **Testing:** `ng test --watch=false` (Vitest)
- **Package Manager:** npm
- **Auth:** Currently mocked via headers (X-User-ID) — Future OAuth2

### Backend Container (`agent-be-container`)
- **Framework:** Aiohttp
- **AI Logic:** LangGraph with PostgreSQL checkpointing
- **LLM:** langchain-google-genai (configurable)
- **Dependency Manager:** Poetry
- **Key Principle:** Construct graphs at startup, not per-request

**Important:** Keep containers independent. Use stable API contracts.

---

## Critical Guidelines

### Specification Maintenance
⚠️ **CRITICAL:** Update spec/ files whenever you add/modify features or change how frontend/backend communicate.

### Atomic Operations
The backend must use atomic SQL operations when verifying access before modifications:
```sql
UPDATE table SET column = $1 WHERE id = $2 AND user_id = $3
```
NOT: SELECT, then UPDATE (prevents race conditions and deadlocks).

### Testing & Verification
- Run `make agent-be-test` before backend changes
- Run `ng test --watch=false` before frontend changes
- Verify tests pass before committing

---

## Recent Changes

| Date | Item | Category | Status |
|------|------|----------|--------|
| 2026-03-15 | RFC Specification System Initialized | DOC | ✅ |

---

## Next Steps

1. **Start with [ARCHITECTURE.md](ARCHITECTURE.md)** — Understand the system design
2. **Review [Requirements Index](requirements/README.md)** — See what's planned/in progress
3. **Check [GAP_ANALYSIS.md](GAP_ANALYSIS.md)** — Identify issues to work on
4. **Pick a requirement** — Start with architecture or features category
5. **Create or update REQ files** — Follow the template structure

---

## Integration Points

- **Frontend ↔ Backend:** Defined via stable API contracts (REQ-F###)
- **Architecture Decisions:** Recorded in ARCHITECTURE.md and REQ-A### files
- **Gaps & Issues:** Tracked in GAP_ANALYSIS.md
- **Work Tracking:** Detailed in individual REQ files

---

## Related Resources

- **Specification System Docs:** `~/.copilot/rfc-spec-system/`
- **Project README:** `../README.md`
- **Frontend README:** `../agent-ui-container/README.md`
- **Backend README:** `../agent-be-container/README.md`
- **Custom Instructions:** See repository root for full guidelines

---

**System Initialized:** 2026-03-15  
**Next Review:** [To be scheduled]  
**Maintained By:** [Your Team/Name]
