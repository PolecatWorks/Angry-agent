-- 001_initial_schema.rollback.sql
-- Rollback for initial schema

DROP INDEX IF EXISTS idx_threads_user_id;
DROP TABLE IF EXISTS threads;
