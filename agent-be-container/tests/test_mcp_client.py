"""
Tests for MCP client initialization and tool management
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
# Instead, rely on pytest rootdir being valid for src package imports

from src.mcp_client import mcp_app_create, MCPObjects, connect_to_mcp_server


class TestMCPClient(unittest.IsolatedAsyncioTestCase):
    """Test MCP client initialization"""

    @patch('src.mcp_client.logger')
    async def test_mcp_client_no_servers(self, mock_logger):
        """Test MCP initialization with no servers configured"""
        from aiohttp import web
        app = web.Application()

        config = MagicMock()
        config.myai.toolbox.mcps = []

        # Mock config in app since connect_to_mcp_server accesses app[keys.config]
        # But wait, connect_to_mcp_server isn't passed config, it gets it from app
        from src import keys
        app[keys.config] = config

        # Run startup handler logic directly
        await connect_to_mcp_server(app)

        # Should log that initialization completed
        found = any("initialization complete" in str(call) for call in mock_logger.info.call_args_list)
        if not found:
            print(f"Log calls: {mock_logger.info.call_args_list}")
        assert found

    def test_mcp_objects_dataclass(self):
        """Test MCPObjects dataclass structure"""
        mcp_objects = MCPObjects()

        assert hasattr(mcp_objects, 'tools_by_mcp')
        assert hasattr(mcp_objects, 'all_tools')
        assert hasattr(mcp_objects, 'resources')
        assert hasattr(mcp_objects, 'prompts')

        # Test get_tools_for_mcp method
        tools = mcp_objects.get_tools_for_mcp("test-mcp")
        assert tools == []


if __name__ == '__main__':
    unittest.main()
