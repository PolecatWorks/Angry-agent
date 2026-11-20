import pytest
from aiohttp import web
from src.main import create_app_with_middleware
from src.config import ServiceConfig


@pytest.fixture
def base_config_dict():
    return {
        "webservice": {
            "url": "http://0.0.0.0:8080",
            "prefix": "/api/angry-agent/v1"
        },
        "persistence": {
            "db": {
                "pool_size": 5,
                "automigrate": False,
                "acquire_timeout": 5,
                "connection": {
                    "url": "postgresql://localhost:5432/agentdb",
                    "username": "postgres",
                    "password": "secretpassword"
                }
            }
        },
        "main_aiclient": {
            "model_provider": "google_genai",
            "context_length": 4096,
            "google_api_key": "dummy_key"
        },
        "packager_aiclient": {
            "model_provider": "google_genai",
            "context_length": 4096,
            "google_api_key": "dummy_key"
        },
        "embedding_client": {
            "model_provider": "google_genai",
            "model": "text-embedding-004",
            "google_api_key": "dummy_key"
        },
        "hams": {
            "url": "http://0.0.0.0:8079",
            "prefix": "hams",
            "shutdownDuration": "PT5S",
            "checks": {
                "timeout": 5,
                "fails": 2,
                "preflights": [],
                "shutdowns": []
            }
        }
    }


def test_routes_with_configured_prefix(base_config_dict):
    """Verify routes are mounted under configured webservice.prefix and root /health is available."""
    config = ServiceConfig(**base_config_dict)
    app = create_app_with_middleware(config)

    routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, 'resource') and r.resource]

    # Health check should be at root /health and /api/angry-agent/v1/health
    assert "/health" in routes
    assert "/api/angry-agent/v1/health" in routes

    # Main resource routes under /api/angry-agent/v1
    assert "/api/angry-agent/v1/chat" in routes
    assert "/api/angry-agent/v1/threads" in routes
    assert "/api/angry-agent/v1/threads/{thread_id}/history" in routes
    assert "/api/angry-agent/v1/threads/{thread_id}/visualizations" in routes
    assert "/api/angry-agent/v1/threads/{thread_id}" in routes
    assert "/api/angry-agent/v1/user/settings" in routes
    assert "/api/angry-agent/v1/agents" in routes
    assert "/api/angry-agent/v1/agents/{agent_id}" in routes

    # Backward compatibility routes under /api
    assert "/api/chat" in routes
    assert "/api/threads" in routes
    assert "/api/threads/{thread_id}/history" in routes
    assert "/api/threads/{thread_id}/visualizations" in routes
    assert "/api/threads/{thread_id}" in routes
    assert "/api/user/settings" in routes
    assert "/api/agents" in routes
    assert "/api/agents/{agent_id}" in routes


def test_routes_fallback_to_url_path(base_config_dict):
    """When webservice.prefix is empty, fall back to webservice.url.path."""
    base_config_dict["webservice"]["prefix"] = ""
    base_config_dict["webservice"]["url"] = "http://0.0.0.0:8080/custom-service"
    config = ServiceConfig(**base_config_dict)
    app = create_app_with_middleware(config)

    routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, 'resource') and r.resource]

    assert "/health" in routes
    assert "/custom-service/health" in routes
    assert "/custom-service/chat" in routes
    assert "/custom-service/threads" in routes
    assert "/api/threads" in routes


def test_routes_default_prefix(base_config_dict):
    """When webservice.prefix is empty and url has no path, default to /api/angry-agent/v1."""
    base_config_dict["webservice"]["prefix"] = ""
    base_config_dict["webservice"]["url"] = "http://0.0.0.0:8080"
    config = ServiceConfig(**base_config_dict)
    app = create_app_with_middleware(config)

    routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, 'resource') and r.resource]

    assert "/health" in routes
    assert "/api/angry-agent/v1/health" in routes
    assert "/api/angry-agent/v1/chat" in routes
    assert "/api/chat" in routes


import json
from aiohttp.test_utils import make_mocked_request

@pytest.mark.asyncio
async def test_health_check_endpoints_response(base_config_dict):
    """Test that GET /health and GET {api_prefix}/health return 200 OK without requiring authentication."""
    config = ServiceConfig(**base_config_dict)
    app = create_app_with_middleware(config)

    found_root = False
    found_prefixed = False
    for route in app.router.routes():
        if route.resource and route.resource.canonical == "/health":
            req = make_mocked_request("GET", "/health", app=app)
            resp = await route.handler(req)
            assert resp.status == 200
            data = json.loads(resp.text)
            assert data == {"status": "ok"}
            found_root = True
        elif route.resource and route.resource.canonical == "/api/angry-agent/v1/health":
            req = make_mocked_request("GET", "/api/angry-agent/v1/health", app=app)
            resp = await route.handler(req)
            assert resp.status == 200
            data = json.loads(resp.text)
            assert data == {"status": "ok"}
            found_prefixed = True

    assert found_root
    assert found_prefixed
