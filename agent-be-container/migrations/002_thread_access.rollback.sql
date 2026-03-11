-- 002_thread_access.rollback.sql
-- Drop thread_access table

DROP INDEX IF EXISTS idx_thread_access_user_id;
DROP TABLE IF EXISTS thread_access;
