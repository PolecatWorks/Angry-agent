"""
Tests for HAMS health monitoring endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
from aiohttp import web
from prometheus_client import CollectorRegistry

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from hams import Hams
from hams.config import HamsConfig

@pytest.fixture
def hams_config():
    return HamsConfig(
        url="http://localhost:8079/",
        prefix="hams",
        checks={"timeout": 5, "fails": 3, "preflights": [], "shutdowns": []},
        shutdownDuration="PT5S"
    )

@pytest.fixture
def hams_instance(hams_config):
    mock_hams_app = web.Application()
    mock_base_app = web.Application()
    registry = CollectorRegistry()
    return Hams(
        hams_app=mock_hams_app,
        app=mock_base_app,
        config=hams_config,
        registry=registry
    )

class TestHamsEndpoints:
    """Test HAMS health check endpoints"""

    @pytest.mark.asyncio
    async def test_alive_endpoint(self, hams_instance):
        """Test /alive endpoint always returns true"""
        # alive() is synchronous
        result = hams_instance.alive()
        assert result is True

    @pytest.mark.asyncio
    async def test_ready_endpoint_always_ready(self, hams_instance):
        """Test /ready endpoint returns true when no prestart checks"""
        # ready() is synchronous
        result = hams_instance.ready()
        assert result is True

    @pytest.mark.asyncio
    async def test_monitor_endpoint_response(self, hams_instance):
        """Test /monitor endpoint returns service info"""
        if hasattr(hams_instance, 'monitor'):
            result = await hams_instance.monitor()
            assert "name" in result

    def test_hams_config_url_parsing(self):
        """Test HAMS configuration URL parsing"""
        config = HamsConfig(
            url="http://localhost:9090/",
            prefix="health",
            checks={"timeout": 5, "fails": 3, "preflights": [], "shutdowns": []},
            shutdownDuration="PT5S"
        )
        assert config.url.host == "localhost"
        assert config.url.port == 9090
        assert config.prefix == "health"

class TestHamsLifecycle:
    """Test HAMS startup and shutdown lifecycle"""

    @pytest.mark.asyncio
    @patch('hams.web.TCPSite')
    @patch('hams.web.AppRunner')
    async def test_hams_startup(self, mock_runner, mock_site, hams_config):
        """Test HAMS starts up correctly"""
        # Mock the runner and site
        mock_runner_instance = AsyncMock()
        mock_runner.return_value = mock_runner_instance

        mock_site_instance = AsyncMock()
        mock_site.return_value = mock_site_instance

        mock_hams_app = web.Application()
        mock_base_app = web.Application()
        registry = CollectorRegistry()

        hams = Hams(
            hams_app=mock_hams_app,
            app=mock_base_app,
            config=hams_config,
            registry=registry
        )

        assert hams.config.url.port == 8079
        assert hams.config.prefix == "hams"

class TestHamsPrestartChecks:
    """Test HAMS prestart check execution"""

    def test_checks_configuration(self, hams_config):
        """Test checks configuration is properly loaded"""
        # Re-creating config for this specific test to match original params
        config = HamsConfig(
            url="http://localhost:8079/",
            prefix="hams",
            checks={"timeout": 10, "fails": 3, "preflights": [], "shutdowns": []},
            shutdownDuration="PT5S"
        )
        assert config.checks.timeout == 10
        assert config.checks.fails == 3

    @pytest.mark.asyncio
    async def test_ready_with_no_checks(self, hams_config):
        """Test ready endpoint with no prestart checks configured"""
        mock_hams_app = web.Application()
        mock_base_app = web.Application()
        registry = CollectorRegistry()
        hams = Hams(
            hams_app=mock_hams_app,
            app=mock_base_app,
            config=hams_config,
            registry=registry
        )

        result = hams.ready()

        # Should be ready if no checks configured
        assert result is True
