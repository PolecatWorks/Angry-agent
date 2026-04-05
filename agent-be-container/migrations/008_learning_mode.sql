-- 008_learning_mode.sql

ALTER TABLE users ADD COLUMN learning_mode_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE threads ADD COLUMN learning_mode_enabled BOOLEAN;
