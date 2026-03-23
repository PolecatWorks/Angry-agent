-- 004_visualizations.sql
CREATE TABLE IF NOT EXISTS visualizations (
    id UUID PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    mfe VARCHAR(255) NOT NULL,
    component VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    description TEXT,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient querying by thread
CREATE INDEX IF NOT EXISTS idx_visualizations_thread_id ON visualizations(thread_id);
