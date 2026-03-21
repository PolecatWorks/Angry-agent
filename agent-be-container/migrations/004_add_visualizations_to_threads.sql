-- 004_add_visualizations_to_threads.sql
-- Add visualizations JSONB column to threads table

ALTER TABLE threads ADD COLUMN visualizations JSONB DEFAULT '[]'::jsonb;
