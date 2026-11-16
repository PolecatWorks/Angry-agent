# Product Requirements Documents (PRDs) Registry

This directory contains the Product Requirements Documents (PRDs) defining the conversational AI, bidirectional MFE Shared Canvas, and semantic data stewardship capabilities of **Angry-Agent (`Angry-agent`)**.

## Document Hierarchy & Structure

| Document | Description |
| :--- | :--- |
| [bidirectional-shared-canvas-mfe-prd.md](./bidirectional-shared-canvas-mfe-prd.md) | **Bidirectional Shared Canvas & Live MFE Co-Editing PRD**: Upgrades `MfeRenderer` and the right-hand AI Workspace panel from one-shot mounting to a live, two-way `MfeCanvasController` (`applyPatch` RFC 6902 JSON Patch, `getState`, self-describing `getSchema`, silent `onStateChange` sync, "Point-and-Ask" `onSelectionChange` focus chips, active-focus locks, and dynamic MFE form switching). |
| [semantic-steward-and-provenance-journey-prd.md](./semantic-steward-and-provenance-journey-prd.md) | **Autonomous Semantic Stewardship, Data Reasoning & Provenance Journey PRD**: Integrates `Angry-agent`'s LangGraph backend (`MultiServerMCPClient`) with `Graphrag` and `data-engine` MCP servers and mounts `data-engine` MFE wrappers (`./DataAssetFormWrapper`, `./JoinHypothesisReviewWrapper`, `./AlgorithmSandboxWrapper`, `./ProvenanceLineageWrapper`) on the RHS canvas. |

## Container-Level & RFC Specifications
- [Frontend Container PRD (`agent-ui-container/spec/prd.md`)](../../agent-ui-container/spec/prd.md)
- [Backend Container PRD (`agent-be-container/spec/prd.md`)](../../agent-be-container/spec/prd.md)
- [Architecture Overview (`spec/ARCHITECTURE.md`)](../ARCHITECTURE.md)
- [RFC Requirements Index (`spec/requirements/README.md`)](../requirements/README.md)
