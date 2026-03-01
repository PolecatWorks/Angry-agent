import asyncpg
from typing import Optional

# Global pool instance
pool: Optional[asyncpg.Pool] = None

from .config import DbOptionsConfig

async def init_db_pool(config: DbOptionsConfig):
    """Initialize database pool with the provided DbOptionsConfig"""
    global pool
    pool = await asyncpg.create_pool(
        dsn=config.connection.dsn,
        max_size=config.pool_size,
        timeout=config.acquire_timeout
    )
    return pool

async def close_db_pool():
    """Close the database pool"""
    global pool
    if pool:
        await pool.close()
        pool = None

async def create_tables(conn: asyncpg.Connection):
    """Create required database tables"""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            color TEXT,
            status_msg TEXT,
            locked_until TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);

        -- Safe migration for existing tables
        ALTER TABLE threads ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE;
        ALTER TABLE threads ADD COLUMN IF NOT EXISTS status_msg TEXT;
    """)

async def get_db_pool() -> asyncpg.Pool:
    """Get the database pool, raising an error if not initialized"""
    if pool is None:
        raise Exception("Database pool not initialized")
    return pool
