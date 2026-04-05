-- 009_remove_learning_mode_from_threads.rollback.sql

ALTER TABLE threads ADD COLUMN learning_mode_enabled BOOLEAN;
