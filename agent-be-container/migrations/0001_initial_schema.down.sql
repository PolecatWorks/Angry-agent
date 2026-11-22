-- 0001_initial_schema.down.sql
-- Revert initial schema for agentrs-be

DROP TABLE IF EXISTS user_settings;
DROP TABLE IF EXISTS agent_definitions;
DROP TABLE IF EXISTS visualizations;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS thread_access;
DROP TABLE IF EXISTS threads;
