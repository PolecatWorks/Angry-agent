-- 002_thread_access.sql
-- Create thread_access table for sharing threads with non-owners

CREATE TABLE IF NOT EXISTS thread_access (
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (thread_id, user_id),
    CONSTRAINT fk_thread_access_thread_id FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_thread_access_user_id ON thread_access(user_id);
