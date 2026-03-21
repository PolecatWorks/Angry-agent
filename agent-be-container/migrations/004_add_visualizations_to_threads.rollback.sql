-- 004_add_visualizations_to_threads.rollback.sql
-- Remove visualizations JSONB column from threads table

ALTER TABLE threads DROP COLUMN IF EXISTS visualizations;
