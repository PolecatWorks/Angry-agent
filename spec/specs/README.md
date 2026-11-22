# Angry-Agent TDD Build Specifications Index

This directory contains the ordered Test-Driven Development (TDD) build specifications derived from [spec/prds/README.md](../prds/README.md).

## Specification Lifecycle Rules
- **`draft`**: Spec is actively being authored or refined prior to implementation.
- **`complete`**: Marked once the spec features and tests are fully implemented and verified.
- **`deprecated`**: Marked when a historical spec is superseded by a newer spec.

---

## Ordered Build Specifications

| Order | Spec File | Status | Derived From PRD | Summary |
| :--- | :--- | :--- | :--- | :--- |
| **01** | [01-ui-bidirectional-mfe-canvas-spec.md](./01-ui-bidirectional-mfe-canvas-spec.md) | `complete` | [bidirectional-shared-canvas-mfe-prd.md](../prds/bidirectional-shared-canvas-mfe-prd.md) | Upgrading `MfeRenderer` (`OnChanges` in-place `applyPatch`, `MfeCanvasController`), `VisualizationsPanel` (`trackByVizId`, silent state sync), and `ChatWindow` ("Point-and-Ask" focus pill & live `canvas_context` payload). |
| **02** | [02-be-shared-canvas-tools-and-endpoints-spec.md](./02-be-shared-canvas-tools-and-endpoints-spec.md) | `complete` | [bidirectional-shared-canvas-mfe-prd.md](../prds/bidirectional-shared-canvas-mfe-prd.md) | Adding `PATCH /api/threads/{thread_id}/visualizations/{viz_id}` for silent state sync, `canvas_context` ingestion in `POST /api/chat`, RFC 6902 `"patch"` reducer action, and generic `inspect_active_mfe`, `patch_active_mfe`, and `switch_active_mfe` LangGraph tools. |
| **03** | [03-keycloak-jwks-auth-and-claims-spec.md](./03-keycloak-jwks-auth-and-claims-spec.md) | `draft` | [service-claims-and-keycloak-auth-prd.md](../prds/service-claims-and-keycloak-auth-prd.md) | Frontend `AuthInterceptor`, backend JWKS token validation, `angry-agent-api` role checks (`agent:execute`, `agent:create`, `agent:admin`), `DataAgentAdmins`/`DataAgentUsers` realm groups, and outbound `angry-agent-sa` M2M tokens. |

