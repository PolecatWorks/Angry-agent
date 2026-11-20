-- 007_visualizations_pin_to_pane.sql
ALTER TABLE visualizations ADD COLUMN pin_to_pane BOOLEAN DEFAULT TRUE;
