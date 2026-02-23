"""
Tests for database connection and table management
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from database import create_tables, init_db_pool, close_db_pool, get_db_pool
from config import DbOptionsConfig, DbConnectionConfig

@pytest.mark.asyncio
async def test_create_tables():
    """Test SQL for creating threads table"""
    mock_conn = AsyncMock()
    await create_tables(mock_conn)

    # Verify execute was called
    assert mock_conn.execute.called

    # Get the SQL executed
    args, _ = mock_conn.execute.call_args
    sql = args[0]

    assert "CREATE TABLE IF NOT EXISTS threads" in sql
    assert "thread_id TEXT PRIMARY KEY" in sql
    assert "user_id TEXT NOT NULL" in sql
    assert "title TEXT" in sql


class TestDatabasePoolLifecycle:
    """Test database connection pool initialization and cleanup"""

    @pytest.mark.asyncio
    @patch('database.asyncpg.create_pool', new_callable=MagicMock)
    async def test_init_db_pool(self, mock_create_pool):
        """Test database pool initialization"""
        mock_pool = AsyncMock()

        # Make the mock return an awaitable that resolves to mock_pool
        async def return_pool(**kwargs):
            return mock_pool

        mock_create_pool.side_effect = return_pool

        dsn = "postgresql://user:pass@localhost:5432/testdb"
        mock_conn = MagicMock(spec=DbConnectionConfig)
        mock_conn.dsn = dsn
        mock_config = MagicMock(spec=DbOptionsConfig)
        mock_config.connection = mock_conn
        mock_config.pool_size = 10
        mock_config.acquire_timeout = 5

        pool = await init_db_pool(mock_config)

        mock_create_pool.assert_called_once_with(
            dsn=dsn,
            max_size=10,
            timeout=5
        )
        assert pool == mock_pool

    @pytest.mark.asyncio
    @patch('database.pool')
    async def test_get_db_pool_initialized(self, mock_pool_var):
        """Test getting initialized database pool"""
        # Set the mock variable effectively
        import database
        mock_pool = AsyncMock()
        database.pool = mock_pool

        try:
            pool = await get_db_pool()
            assert pool == mock_pool
        finally:
            database.pool = None

    @pytest.mark.asyncio
    async def test_close_db_pool(self):
        """Test closing database pool"""
        mock_pool = AsyncMock()
        import database
        database.pool = mock_pool

        try:
            await close_db_pool()
            mock_pool.close.assert_called_once()
            assert database.pool is None
        finally:
            database.pool = None

    @pytest.mark.asyncio
    async def test_get_db_pool_not_initialized(self):
        """Test error when getting pool before initialization"""
        import database
        database.pool = None

        with pytest.raises(Exception, match="Database pool not initialized"):
            await get_db_pool()
