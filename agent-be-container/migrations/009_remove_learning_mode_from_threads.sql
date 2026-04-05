-- 009_remove_learning_mode_from_threads.sql

ALTER TABLE threads DROP COLUMN learning_mode_enabled;
