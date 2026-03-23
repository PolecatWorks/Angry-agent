import asyncpg
from typing import Optional

# Global pool instance
pool: Optional[asyncpg.Pool] = None

from src.config import DbOptionsConfig

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

async def get_db_pool() -> asyncpg.Pool:
    """Get the database pool, raising an error if not initialized"""
    if pool is None:
        raise Exception("Database pool not initialized")
    return pool
