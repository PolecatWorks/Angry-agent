-- 008_learning_mode.rollback.sql

ALTER TABLE threads DROP COLUMN learning_mode_enabled;
ALTER TABLE users DROP COLUMN learning_mode_enabled;
