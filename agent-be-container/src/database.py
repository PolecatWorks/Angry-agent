import os
import asyncpg
from typing import Optional

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mysecretpassword")
DB_NAME = os.getenv("POSTGRES_DB", "agentdb")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

pool: Optional[asyncpg.Pool] = None

async def init_db_pool():
    global pool
    # Wait for DB to be ready potentially, but for now just create pool
    pool = await asyncpg.create_pool(dsn=DSN)
    return pool

async def close_db_pool():
    global pool
    if pool:
        await pool.close()

async def create_tables(conn: asyncpg.Connection):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
    """)

async def get_db_pool() -> asyncpg.Pool:
    if pool is None:
        raise Exception("Database pool not initialized")
    return pool
