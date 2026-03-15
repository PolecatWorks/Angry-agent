# REQ-D009: Database Schema Documentation

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Document the complete PostgreSQL database schema for the Angry-Agent backend. Specify all tables, columns, constraints, indexes, and relationships. Provide Entity-Relationship Diagram (ERD) and migration strategy documentation.

---

## Rationale

Database schema must be clearly documented:
- New developers need to understand data model
- Migrations must be traceable and reversible
- Schema changes require review and planning
- Performance relies on proper indexing
- Referential integrity must be maintained
- Audit trail needed for data changes

---

## Key Implementation Points

1. **Schema Definition** — Document all tables and columns
2. **Data Types** — Specify correct types for each field
3. **Constraints** — Primary keys, foreign keys, unique, not null
4. **Indexes** — Performance indexes on frequently queried columns
5. **Relationships** — ERD showing table relationships
6. **Migrations** — Version control for schema changes
7. **Views** — Any database views needed
8. **Permissions** — User roles and permissions

---

## Current Status

💡 **PROPOSED** — Schema created ad-hoc. Full documentation and migrations needed.

---

## Work Items

### 🟠 WORK-D002-001: Document Schema Tables

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-4 hours  
**Description:** Document all database tables and columns

**Problem:**
- Schema not documented
- Table purposes unclear
- Column types unknown
- Constraints not specified

**Solution:**
- Create schema documentation file
- List all tables with descriptions
- Document each column: name, type, purpose
- Specify all constraints
- Document indexes and relationships

**Files to Change:**
- `agent-be-container/docs/DATABASE.md` (create)
- `agent-be-container/docs/SCHEMA.md` (create)

**Acceptance Criteria:**
- [ ] All tables documented
- [ ] All columns with types documented
- [ ] All constraints listed
- [ ] All indexes documented
- [ ] Relationships clear
- [ ] ERD diagram included
- [ ] Documentation complete and accurate

**Related Issues:** [GAP_ANALYSIS.md Issue #2 (Database Schema)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002 (backend with database)

---

### 🟡 WORK-D002-002: Create Database Migrations

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Set up Alembic or similar for schema versioning

**Problem:**
- No migration strategy
- Schema changes not tracked
- Difficult to reproduce in other environments
- Cannot rollback changes

**Solution:**
- Set up Alembic for migrations
- Create initial migration from current schema
- Document migration workflow
- Provide rollback procedures

**Files to Change:**
- `agent-be-container/migrations/` (create if missing)
- `alembic.ini` (configure)
- `agent-be-container/docs/MIGRATIONS.md`

**Acceptance Criteria:**
- [ ] Alembic configured
- [ ] Initial migration created
- [ ] Migration up/down working
- [ ] Workflow documented
- [ ] Rollback tested
- [ ] Tests passing

**Related Issues:** None

**Dependencies:** WORK-D002-001

---

### 🟢 WORK-D002-003: Create ERD Diagram

**Priority:** 🟢 LOW  
**Status:** ⏳ PENDING  
**Effort:** 1-2 hours  
**Description:** Generate Entity-Relationship Diagram of database

**Problem:**
- Relationships not visualized
- Difficult to understand data model
- New developers confused by schema

**Solution:**
- Create ERD diagram (using Mermaid or similar)
- Show all tables and relationships
- Include cardinality (1:1, 1:N, M:N)
- Add to documentation

**Files to Change:**
- `agent-be-container/docs/DATABASE.md` (add diagram)

**Acceptance Criteria:**
- [ ] ERD diagram created
- [ ] All tables included
- [ ] All relationships shown
- [ ] Diagram legible and clear
- [ ] Documentation explains relationships
- [ ] Diagram kept up-to-date

**Related Issues:** None

**Dependencies:** WORK-D002-001

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — Database persistence
- [REQ-F007: Conversation History & Persistence](../features/REQ-F007.md) — Message storage

---

## Notes

### Key Tables (Conceptual)

**Sessions:**
- Conversation sessions with user_id and timestamps

**Messages:**
- Individual messages with role (user/assistant)
- Links to session and timestamps

**LangGraph Checkpoints:**
- State snapshots for agent recovery
- Indexed by session_id

**Users:**
- User account information (if OAuth2 implemented)

### Indexing Strategy

- Primary keys auto-indexed
- Foreign keys indexed
- Frequently queried columns indexed
- Composite indexes for common queries

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
