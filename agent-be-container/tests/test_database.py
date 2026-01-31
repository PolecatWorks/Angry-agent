import unittest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from database import create_tables

class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def test_create_tables(self):
        mock_conn = AsyncMock()
        await create_tables(mock_conn)

        # Verify execute was called
        self.assertTrue(mock_conn.execute.called)

        # Get the SQL executed
        args, _ = mock_conn.execute.call_args
        sql = args[0]

        self.assertIn("CREATE TABLE IF NOT EXISTS threads", sql)
        self.assertIn("thread_id TEXT PRIMARY KEY", sql)
        self.assertIn("user_id TEXT NOT NULL", sql)

if __name__ == '__main__':
    unittest.main()
