# SPEC-04: Persistence, Agent-as-Data & GraphRAG Concepts

## 1. Scope & Objective
Incorporate design concepts inspired by:
- **`PolecatWorks/agent-as-data`**: Treating agent metadata, capabilities, tools, active schemas, and interaction traces as structured, versioned, relational entities rather than ephemeral runtime objects.
- **`PolecatWorks/Graphrag`**: Relational knowledge indexing and PostgreSQL graph storage for document/field metadata and entity relationships.

## 2. Agent-as-Data Schema Representation
Every agent session and form artifact can be serialized and queried:
- `AgentDescriptor`: Name, version, system prompt template, bound tool definitions.
- `FormDefinition`: Registered MFE form schemas, field relationships, and semantic descriptions.
- `TraceRecord`: Fine-grained history of every patch, user focus event, and agent action.

## 3. Storage Architecture
- In-memory runtime layer (`DashMap`) for ultra-low latency (<5ms) state synchronization during active user typing.
- PostgreSQL schema for durable thread state, snapshots, and graph relationships between form fields and entities (allowing GraphRAG semantic lookups if needed).
