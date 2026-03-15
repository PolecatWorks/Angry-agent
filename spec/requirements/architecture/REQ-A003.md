# REQ-A003: Authentication & Authorization

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Implement a production-ready authentication and authorization system for the Angry-Agent application. Replace current header-based mocking with OAuth2 integration, session management, and role-based access control (RBAC) across both frontend and backend containers.

---

## Rationale

Current header-based authentication is:
- Trivial to spoof (security risk)
- Not production-safe
- Provides no audit trail
- Cannot track user actions
- Blocks production deployment

A robust system is needed that:
- Securely authenticates users
- Maintains secure sessions
- Supports role-based access
- Enables audit logging
- Works across containers
- Supports future OAuth2 migration

---

## Key Implementation Points

1. **OAuth2 Integration** — Replace header-based auth with OAuth2 flows
2. **JWT Tokens** — Use JWT for stateless API authentication
3. **Session Management** — Store sessions securely (Redis or database)
4. **RBAC** — Implement role and permission checks
5. **Protected Endpoints** — Enforce auth on all API routes
6. **Audit Logging** — Log all authentication events
7. **Token Refresh** — Implement secure token refresh strategy
8. **User Context** — Make user info available to all services

---

## Current Status

💡 **PROPOSED** — Authentication currently uses basic header mocking. Full OAuth2/JWT implementation planned.

---

## Work Items

### 🔴 WORK-A003-001: Implement OAuth2 Provider Integration

**Priority:** 🔴 CRITICAL  
**Status:** ⏳ PENDING  
**Effort:** 6-8 hours  
**Description:** Integrate OAuth2 provider (Google, Auth0, or custom) for user authentication

**Problem:**
- No real authentication mechanism
- Users can be anyone by spoofing headers
- No identity provider integration
- Cannot deploy to production

**Solution:**
- Choose OAuth2 provider (recommend: Auth0 or custom)
- Implement OAuth2 flow (authorization code with PKCE)
- Handle token exchange
- Validate tokens on API calls
- Create user record on first login

**Files to Change:**
- `agent-be-container/app/auth/` (create if missing)
- `agent-be-container/app/auth/oauth2.py`
- `agent-ui-container/src/app/auth/` (create if missing)
- `agent-ui-container/src/app/auth/oauth2.service.ts`

**Acceptance Criteria:**
- [ ] OAuth2 login flow working end-to-end
- [ ] Tokens generated and validated correctly
- [ ] User information stored (name, email, ID)
- [ ] Token expiration handled
- [ ] Logout clears tokens
- [ ] Works with chosen provider

**Related Issues:** [GAP_ANALYSIS.md Issue #1 (Production Auth)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002 (backend server must be ready)

---

### 🟠 WORK-A003-002: Implement JWT Token Management

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 4-5 hours  
**Description:** Set up JWT token generation, validation, and refresh mechanisms

**Problem:**
- No token-based authentication
- Tokens not validated server-side
- No refresh token strategy
- Token expiration not handled

**Solution:**
- Implement JWT creation with proper claims
- Add token validation middleware
- Implement refresh token flow
- Handle token expiration
- Secure token storage (httpOnly cookies)

**Files to Change:**
- `agent-be-container/app/auth/jwt.py`
- `agent-be-container/app/middleware/auth.py`

**Acceptance Criteria:**
- [ ] JWT tokens generated with correct claims
- [ ] Tokens validated on protected endpoints
- [ ] Expired tokens rejected
- [ ] Refresh token flow working
- [ ] Token stored securely
- [ ] All tests passing

**Related Issues:** [GAP_ANALYSIS.md Issue #1 (Production Auth)](../../GAP_ANALYSIS.md)

**Dependencies:** WORK-A003-001 (OAuth2 integration)

---

### 🟠 WORK-A003-003: Implement Role-Based Access Control (RBAC)

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-4 hours  
**Description:** Add role and permission system for API endpoints

**Problem:**
- No authorization beyond authentication
- All users have same access level
- Cannot restrict features by role
- No permission checking

**Solution:**
- Define user roles (user, admin, etc.)
- Implement permission decorators
- Add role checks to API endpoints
- Store roles in user record
- Log authorization failures

**Files to Change:**
- `agent-be-container/app/auth/permissions.py`
- `agent-be-container/app/auth/decorators.py`
- `agent-be-container/app/models/user.py`

**Acceptance Criteria:**
- [ ] Roles defined and assigned to users
- [ ] Permission decorators working
- [ ] Protected endpoints enforce permissions
- [ ] Unauthorized requests rejected with 403
- [ ] Audit log captures permission failures
- [ ] Tests cover all role scenarios

**Related Issues:** [GAP_ANALYSIS.md Issue #1 (Production Auth)](../../GAP_ANALYSIS.md)

**Dependencies:** WORK-A003-002 (JWT implementation)

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — Integrates auth at API layer
- [REQ-F007: Core API Endpoints](../features/REQ-F007.md) — All endpoints require auth
- [REQ-D011: Deployment & Operations Guide](../documentation/REQ-D011.md) — Auth configuration for production

---

## Notes

### Current vs. Future State

**Current (Development):**
- Header-based authentication (X-User-ID)
- No real user identity
- No session management
- No audit trail

**Future (Production):**
- OAuth2 integration
- JWT tokens with expiration
- Session management
- Full audit logging
- Role-based access control
- Secure token storage

### Implementation Notes

- Use PKCE flow for OAuth2 (browser-based)
- Store tokens in httpOnly cookies (not localStorage)
- Refresh tokens have longer expiry than access tokens
- All auth endpoints should be HTTPS only
- Consider implementing multi-factor authentication (MFA) in Phase 2

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
