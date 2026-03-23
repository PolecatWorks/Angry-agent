-- 005_agent_definitions.rollback.sql
-- Rollback vector extension and tables

DROP TABLE IF EXISTS agent_definition_chunks;
DROP TABLE IF EXISTS agent_definitions;

-- We typically shouldn't drop the vector extension as other things might use it eventually,
-- but we can for a strict rollback if we are sure. However, it's safer to leave it.
-- DROP EXTENSION IF EXISTS vector;
