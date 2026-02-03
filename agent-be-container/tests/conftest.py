"""
Pytest fixtures and configuration for all tests
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from config import ServiceConfig
from aiohttp import web
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def test_config_path():
    """Path to test configuration YAML file"""
    return Path(__file__).parent / "test_data" / "config.yaml"


@pytest.fixture
def test_secrets_path():
    """Path to test secrets directory"""
    return Path(__file__).parent / "test_data" / "secrets"


@pytest.fixture
def sample_config(test_config_path, test_secrets_path):
    """Load a sample ServiceConfig for testing"""
    return ServiceConfig.from_yaml_and_secrets_dir(
        yaml_file=test_config_path,
        secrets_path=test_secrets_path
    )


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    pool = AsyncMock()
    conn = AsyncMock()

    # Setup connection acquisition
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None

    return pool


@pytest.fixture
def mock_checkpointer():
    """Mock LangGraph checkpointer"""
    return MemorySaver()


@pytest.fixture
async def aiohttp_app():
    """Create a fresh aiohttp application for testing"""
    app = web.Application()
    yield app
    await app.cleanup()


@pytest.fixture
def aiohttp_client(aiohttp_app, aiohttp_client):
    """Create an aiohttp test client"""
    return aiohttp_client(aiohttp_app)
