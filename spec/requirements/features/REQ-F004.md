# REQ-F004: Core API Endpoints

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Define and document the complete REST API contract between the frontend and backend containers. Specify all endpoints, request/response schemas, error codes, and authentication requirements. Provide OpenAPI specification for client code generation.

---

## Rationale

Frontend and backend must communicate via well-defined API contract:
- Prevents misalignment between frontend expectations and backend implementation
- Enables parallel development of frontend and backend
- Allows auto-generation of client libraries
- Provides clear documentation for new developers
- Enables API versioning and backward compatibility
- Allows contract-first testing

---

## Key Implementation Points

1. **RESTful Design** — Follow REST principles for endpoint design
2. **OpenAPI Specification** — Maintain OpenAPI 3.0+ spec for all endpoints
3. **Versioning** — Support API versioning (e.g., /api/v1/)
4. **Authentication** — All endpoints require valid authentication
5. **Error Responses** — Consistent error response format
6. **Request Validation** — Validate all inputs with clear error messages
7. **Response Pagination** — Paginate list endpoints (limit, offset)
8. **Rate Limiting** — Implement rate limiting per user/endpoint

---

## Current Status

💡 **PROPOSED** — API endpoints exist but are not formally documented. OpenAPI spec needs to be created.

---

## Work Items

### 🟠 WORK-F004-001: Define OpenAPI Specification

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-4 hours  
**Description:** Create comprehensive OpenAPI 3.0 specification for all endpoints

**Problem:**
- No formal API documentation
- Frontend developers must read backend code to understand API
- Cannot auto-generate client libraries
- No versioning strategy defined
- Unclear which endpoints are stable

**Solution:**
- Create OpenAPI 3.0 spec file
- Document all current endpoints
- Define request/response schemas
- Specify error codes and formats
- Document authentication requirements
- Document pagination strategy

**Files to Change:**
- `agent-be-container/openapi.yaml` (create)
- `agent-be-container/app/api/` (add docstrings)

**Acceptance Criteria:**
- [ ] OpenAPI spec covers all endpoints
- [ ] All request/response schemas defined
- [ ] Authentication documented
- [ ] Error codes documented
- [ ] Can serve spec on /api/docs endpoint
- [ ] Swagger UI working

**Related Issues:** [GAP_ANALYSIS.md Issue #3 (API Contract)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002 (backend server)

---

### 🟠 WORK-F004-002: Implement Chat Endpoints

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-4 hours  
**Description:** Create REST endpoints for chat interactions with agent

**Problem:**
- Chat endpoint implementation vague
- Request/response format undefined
- Streaming vs. non-streaming behavior unclear
- Session management approach not defined

**Solution:**
- Create POST /api/v1/chat endpoint
- Handle user messages and agent responses
- Manage conversation session
- Return proper error codes
- Implement request validation

**Files to Change:**
- `agent-be-container/app/api/chat.py`
- `agent-be-container/app/models/` (chat-related models)

**Acceptance Criteria:**
- [ ] POST /api/v1/chat accepts user message
- [ ] Returns agent response with proper schema
- [ ] Session ID handled correctly
- [ ] Input validation working
- [ ] Error codes returned correctly
- [ ] Rate limiting enforced

**Related Issues:** [GAP_ANALYSIS.md Issue #3 (API Contract)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002, REQ-A003

---

### 🟡 WORK-F004-003: Implement Session Management Endpoints

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Create endpoints for managing chat sessions and history

**Problem:**
- Session listing undefined
- History retrieval unclear
- Session deletion not specified
- Cannot manage multiple conversations

**Solution:**
- Create GET /api/v1/sessions endpoint
- Create GET /api/v1/sessions/{id} endpoint
- Create GET /api/v1/sessions/{id}/messages endpoint
- Create DELETE /api/v1/sessions/{id} endpoint
- Implement pagination and filtering

**Files to Change:**
- `agent-be-container/app/api/sessions.py`

**Acceptance Criteria:**
- [ ] List sessions endpoint working
- [ ] Get session details endpoint working
- [ ] Get session history endpoint working
- [ ] Delete session endpoint working
- [ ] Pagination working
- [ ] User isolation enforced

**Related Issues:** None

**Dependencies:** WORK-F004-002 (chat endpoints)

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — Backend implements these endpoints
- [REQ-A003: Authentication & Authorization](../architecture/REQ-A003.md) — Auth required on all endpoints
- [REQ-F005: Chat Interface Component](../features/REQ-F005.md) — Frontend UI calls these endpoints
- [REQ-F007: Conversation History & Persistence](../features/REQ-F007.md) — Uses session endpoints

---

## Notes

### API Design Principles

- **Resource-Oriented:** Design around resources (chat, sessions, messages)
- **Standard HTTP Methods:** GET (read), POST (create), PUT (update), DELETE (delete)
- **Consistent Response Format:** All responses use same structure
- **Clear Error Messages:** Errors include actionable feedback
- **Stateless:** Each request contains all context (via tokens)
- **Versioning:** API version in URL (/api/v1/, /api/v2/)

### Response Format

```json
{
  "success": true,
  "data": { /* response data */ },
  "error": null,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "User provided description",
    "details": {}
  }
}
```

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
