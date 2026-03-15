# REQ-D008: Development Setup Guide

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Create comprehensive documentation for setting up the Angry-Agent development environment. Guide new developers through prerequisites, local environment configuration, running services, and troubleshooting common issues for both frontend and backend containers.

---

## Rationale

New developers need clear setup instructions:
- Reduces onboarding time
- Prevents setup errors
- Documents prerequisites
- Provides troubleshooting guide
- Standardizes development environment
- Enables quick local testing

---

## Key Implementation Points

1. **Prerequisites** — System requirements, versions
2. **Frontend Setup** — Node, npm, dependencies, running locally
3. **Backend Setup** — Python, Poetry, dependencies, running locally
4. **Database Setup** — PostgreSQL installation and initialization
5. **Environment Variables** — Configuration for development
6. **Running Services** — Step-by-step to start all services
7. **Testing** — How to run tests locally
8. **Troubleshooting** — Common issues and solutions

---

## Current Status

💡 **PROPOSED** — Setup guide needs to be written and tested.

---

## Work Items

### 🟡 WORK-D001-001: Write Frontend Setup Guide

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Document frontend development environment setup

**Problem:**
- No clear frontend setup instructions
- Unclear Node/npm version requirements
- Setup process not documented
- New developers struggle with setup

**Solution:**
- Document Node.js requirements
- List npm dependencies needed
- Step-by-step setup instructions
- Troubleshooting common errors
- Provide verification steps

**Files to Change:**
- `agent-ui-container/README.md` (setup section)
- Create `agent-ui-container/SETUP.md` (detailed guide)
- Create `.nvmrc` file for Node version

**Acceptance Criteria:**
- [ ] Prerequisites clearly listed
- [ ] Setup steps numbered and clear
- [ ] Verification steps included
- [ ] Troubleshooting section complete
- [ ] New developer can set up in <30 min
- [ ] Tested with fresh clone

**Related Issues:** [GAP_ANALYSIS.md Issue #5 (Deployment)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A001 (frontend architecture)

---

### 🟡 WORK-D001-002: Write Backend Setup Guide

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Document backend development environment setup

**Problem:**
- No clear backend setup instructions
- Python version not specified
- Poetry setup unclear
- Database connection configuration missing

**Solution:**
- Document Python 3.11+ requirement
- Explain Poetry installation
- Step-by-step dependency installation
- Database connection setup
- Environment variable configuration

**Files to Change:**
- `agent-be-container/README.md` (setup section)
- Create `agent-be-container/SETUP.md` (detailed guide)
- Create `.python-version` file for Python version
- Create `.env.example` file

**Acceptance Criteria:**
- [ ] Prerequisites clearly listed
- [ ] Setup steps numbered and clear
- [ ] Poetry commands documented
- [ ] Database setup included
- [ ] Verification steps included
- [ ] New developer can set up in <30 min
- [ ] Tested with fresh clone

**Related Issues:** [GAP_ANALYSIS.md Issue #5 (Deployment)](../../GAP_ANALYSIS.md)

**Dependencies:** REQ-A002 (backend architecture)

---

### 🟢 WORK-D001-003: Create Troubleshooting Guide

**Priority:** 🟢 LOW  
**Status:** ⏳ PENDING  
**Effort:** 1-2 hours  
**Description:** Document common setup issues and solutions

**Problem:**
- No troubleshooting guide
- Setup errors not documented
- Developers stuck on unknown issues
- Time wasted on common problems

**Solution:**
- List common setup errors
- Provide solutions for each
- Include debug commands
- Link to relevant documentation
- Update with new issues as found

**Files to Change:**
- Create `TROUBLESHOOTING.md`
- Update both README files with link

**Acceptance Criteria:**
- [ ] Common issues documented (10+)
- [ ] Clear solutions provided
- [ ] Debug commands included
- [ ] Links to external resources
- [ ] Updated based on user feedback
- [ ] Tests of solutions performed

**Related Issues:** None

**Dependencies:** WORK-D001-001, WORK-D001-002

---

## Implementation Results

*To be updated when work is completed*

### Changes Made
- [To be documented]

### Verification Checklist
- [ ] [To be verified]

---

## Related Requirements

- [REQ-A001: Frontend Container Architecture](../architecture/REQ-A001.md) — Frontend setup details
- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — Backend setup details

---

## Notes

### Minimum Requirements

**Frontend:**
- Node.js 18+ (use .nvmrc for 20 LTS)
- npm 9+
- 2GB disk space
- Modern browser

**Backend:**
- Python 3.11+
- Poetry 1.5+
- PostgreSQL 14+ (or Docker)
- 2GB RAM

### Quick Start Command

```bash
# After prerequisites installed
make dev  # starts both containers
# or individual:
make agent-ui-dev
make agent-be-dev
```

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
