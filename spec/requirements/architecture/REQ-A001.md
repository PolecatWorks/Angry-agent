# REQ-A001: Frontend Container Architecture

**Status:** PROPOSED  
**Version:** 1.0  
**Proposed:** 2026-03-15  
**Supersedes:** None  
**Superseded by:** None

---

## Description

Establish the frontend container architecture for the Angry-Agent application using Angular with Native Federation Module Federation. Define the structural foundation, routing strategy, component organization, and deployment configuration for the frontend Micro-Frontend (MFE) application.

---

## Rationale

The frontend needs a modern, scalable architecture that:
- Supports modular component development via Native Federation
- Leverages Angular Material for consistent UI
- Enables independent development and deployment
- Allows reusable components across features
- Maintains type safety with TypeScript
- Supports comprehensive testing with Vitest

---

## Key Implementation Points

1. **Native Federation Setup** — Configure @angular-architects/native-federation for module federation
2. **Route-Based Remotes** — Use route configurations for remote modules
3. **Shared Dependencies** — Define shared library versions in federation config
4. **Component Library** — Organize reusable components in shared library structure
5. **TypeScript Configuration** — Maintain strict TypeScript settings for type safety
6. **Build Optimization** — Configure build for production and development
7. **Testing Framework** — Use Vitest with ng test command
8. **Environment Configuration** — Manage different configurations for development/production

---

## Current Status

💡 **PROPOSED** — Frontend architecture ready to be documented and standardized.

---

## Work Items

### 🟠 WORK-A001-001: Configure Native Federation

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 4-6 hours  
**Description:** Set up and configure Native Federation in angular.json and federation.config.ts

**Problem:**
- No formal federation configuration exists
- Developers don't have clear guidance on federation setup
- Module boundaries undefined

**Solution:**
- Create federation.config.ts with proper remote configurations
- Define shared dependencies (Angular, RxJS, Material, etc.)
- Configure route-based module loading
- Document federation strategy

**Files to Change:**
- `agent-ui-container/angular.json`
- `agent-ui-container/federation.config.ts` (create if missing)
- `agent-ui-container/src/app/routes/` (organize route configs)

**Acceptance Criteria:**
- [ ] federation.config.ts properly configured with remotes
- [ ] Shared dependencies defined with correct versions
- [ ] Route-based federation working in dev and production
- [ ] Documentation updated in ARCHITECTURE.md
- [ ] Build succeeds without warnings

**Related Issues:** [GAP_ANALYSIS.md Issue #5 (Deployment)](../GAP_ANALYSIS.md)

**Dependencies:** None

---

### 🟠 WORK-A001-002: Establish Component Structure

**Priority:** 🟠 HIGH  
**Status:** ⏳ PENDING  
**Effort:** 3-4 hours  
**Description:** Define and implement component organization strategy

**Problem:**
- No clear component structure
- Difficult to understand which components are shared vs. feature-specific
- Component reuse is ad-hoc

**Solution:**
- Create `shared/` directory for reusable components
- Create `features/` directory for feature-specific components
- Document component naming conventions
- Create component templates

**Files to Change:**
- `agent-ui-container/src/app/shared/` (create directory structure)
- `agent-ui-container/src/app/features/` (organize features)
- `agent-ui-container/README.md` (document structure)

**Acceptance Criteria:**
- [ ] Shared components directory created and organized
- [ ] Feature-specific components directory structure defined
- [ ] Component naming conventions documented
- [ ] Example components follow structure
- [ ] Documentation updated

**Related Issues:** [GAP_ANALYSIS.md Issue #7 (Frontend Components)](../GAP_ANALYSIS.md)

**Dependencies:** None

---

### 🟡 WORK-A001-003: Configure Development Environment

**Priority:** 🟡 MEDIUM  
**Status:** ⏳ PENDING  
**Effort:** 2-3 hours  
**Description:** Document and validate development environment setup

**Problem:**
- New developers unclear on setup steps
- Environment configuration not documented
- Prerequisites not clearly stated

**Solution:**
- Document Node.js version requirements
- Create setup script or guide
- Document npm commands
- Verify all development tools work

**Files to Change:**
- `agent-ui-container/README.md` (setup section)
- `agent-ui-container/.nvm/` or `.nvmrc` (Node version)
- Create `agent-ui-container/SETUP.md` (detailed guide)

**Acceptance Criteria:**
- [ ] Setup guide clearly documented
- [ ] Prerequisites listed (Node, npm, etc.)
- [ ] Commands clearly explained
- [ ] New developer can set up in <30 minutes
- [ ] Tested with fresh checkout

**Related Issues:** [GAP_ANALYSIS.md Issue #5 (Deployment)](../GAP_ANALYSIS.md)

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

- [REQ-A002: Backend Container Architecture](../architecture/REQ-A002.md) — Works with backend via API
- [REQ-F007: Core API Endpoints](../features/REQ-F007.md) — Frontend calls these endpoints
- [REQ-F005: Chat Interface Component](../features/REQ-F005.md) — UI component for frontend
- [REQ-D008: Development Setup Guide](../documentation/REQ-D008.md) — Setup documentation

---

## Notes

### Frontend Technology Stack (Current)
- **Angular:** 18+
- **UI Framework:** Angular Material
- **Module Federation:** @angular-architects/native-federation
- **Language:** TypeScript (strict mode)
- **Testing:** Vitest (via ng test)
- **Package Manager:** npm

### Key Decisions
- **Why Native Federation?** — Built-in Angular support, better TypeScript integration, simpler than Webpack plugins
- **Why Angular Material?** — Consistent design system, accessibility built-in, good for rapid UI development
- **Why TypeScript strict mode?** — Catches errors at compile time, improves code quality, better IDE support

### Future Considerations
- Component documentation generation
- Visual regression testing
- E2E testing with Cypress/Playwright
- Design token system
- Storybook component library

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial requirement | PROPOSED |
