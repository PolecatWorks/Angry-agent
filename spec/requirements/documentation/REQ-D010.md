# REQ-D010: Testing Strategy & Guidelines

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Establish comprehensive testing strategy and guidelines for the Angry-Agent project. Define testing levels (unit, integration, E2E), coverage expectations, test organization, and best practices for both frontend and backend.

---

## Rationale

Testing ensures code quality and reliability:
- Catches bugs before production
- Enables refactoring with confidence
- Documents expected behavior
- Provides examples for new developers
- Prevents regressions
- Improves code design

---

## Key Implementation Points

1. **Test Levels** — Unit, integration, E2E tests
2. **Coverage Goals** — Minimum coverage percentages
3. **Test Organization** — Directory structure and naming
4. **Frontend Testing** — Angular/Vitest patterns
5. **Backend Testing** — Python/pytest patterns
6. **CI/CD Integration** — Automated test running
7. **Test Data** — Fixtures and factories
8. **Coverage Reports** — Tracking and visibility

---

## Current Status

💡 **PROPOSED** — Testing framework exists per container. Strategy and guidelines need documentation.

---

## Work Items

### 🟡 WORK-D003-001: Document Frontend Testing Strategy

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Create frontend testing guidelines using Vitest/Angular testing

**Problem:**
- No testing guidelines
- Test organization unclear
- Coverage expectations unknown
- Inconsistent test quality

**Solution:**
- Document unit testing patterns for components
- Document service testing patterns
- Provide example test files
- Define coverage expectations
- Document test runners and commands

**Files to Change:**
- `agent-ui-container/TESTING.md` (create)
- `agent-ui-container/README.md` (add testing section)

**Acceptance Criteria:**
- [ ] Unit test examples provided
- [ ] Component testing documented
- [ ] Service testing documented
- [ ] Coverage expectations clear
- [ ] Test organization structure defined
- [ ] Test commands documented
- [ ] Examples working

**Related Issues:** [GAP_ANALYSIS.md Issue #4 (Testing Strategy)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A001 (frontend architecture)

---

### 🟡 WORK-D003-002: Document Backend Testing Strategy

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Create backend testing guidelines using pytest

**Problem:**
- No testing guidelines
- Test organization unclear
- Coverage expectations unknown
- Inconsistent test quality

**Solution:**
- Document unit testing patterns for handlers
- Document integration tests for API endpoints
- Provide example test files
- Define coverage expectations
- Document test runners and commands

**Files to Change:**
- `agent-be-container/TESTING.md` (create)
- `agent-be-container/README.md` (add testing section)

**Acceptance Criteria:**
- [ ] Unit test examples provided
- [ ] Integration test examples provided
- [ ] Coverage expectations clear
- [ ] Test organization structure defined
- [ ] Test commands documented
- [ ] Examples working
- [ ] pytest configuration documented

**Related Issues:** [GAP_ANALYSIS.md Issue #4 (Testing Strategy)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002 (backend architecture)

---

### 🟢 WORK-D003-003: Set Up Coverage Tracking

**Priority:** 🟢 LOW  
**Status:** ⏳ PENDING  
**Effort:** 1-2 hours  
**Description:** Configure coverage reporting and CI/CD integration

**Problem:**
- Coverage not tracked
- No visibility into test quality
- No enforcement of coverage standards

**Solution:**
- Configure coverage tools (Istanbul/NYC for frontend, pytest-cov for backend)
- Add coverage reports to CI/CD
- Set minimum coverage thresholds
- Generate coverage badges

**Files to Change:**
- GitHub Actions workflows
- `.nyc.rc` or similar (frontend)
- `pytest.ini` (backend)

**Acceptance Criteria:**
- [ ] Coverage reports generated
- [ ] Reports in CI/CD
- [ ] Minimum coverage enforced
- [ ] Coverage trending tracked
- [ ] Reports accessible

**Related Issues:** None

**Dependencies:** WORK-D003-001, WORK-D003-002

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A001: Frontend Container Architecture](../architecture/REQ-A001.md) — Component testing
- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — API testing

---

## Notes

### Coverage Goals

**Minimum Target:**
- Frontend: 80% statement coverage
- Backend: 85% statement coverage
- Critical paths: 100%

**Coverage Exceptions:**
- Third-party code: not required
- Auto-generated code: not required
- Type definitions: not required

### Test Organization

**Frontend:**
```
src/
├── app/features/
│   ├── chat/
│   │   ├── chat.component.ts
│   │   └── chat.component.spec.ts    ← Same directory
├── services/
│   ├── chat.service.ts
│   └── chat.service.spec.ts          ← Same directory
```

**Backend:**
```
app/
├── api/
│   ├── chat.py
tests/
├── api/
│   └── test_chat.py                  ← Parallel structure
```

### Testing Frameworks

**Frontend:**
- Test Runner: Vitest or Karma
- Framework: Jasmine
- Utilities: @angular/core/testing

**Backend:**
- Framework: pytest
- Mocking: pytest-mock or unittest.mock
- Fixtures: pytest fixtures

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
