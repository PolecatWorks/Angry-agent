from aiohttp import web
from .config import ServiceConfig
from prometheus_client import CollectorRegistry
import logging
from .hams import Hams, hams_app_create
from ruamel.yaml import YAML
import io
from .mcp_client import mcp_app_create

# from chatbot.service import service_app_create
from . import keys

logger = logging.getLogger(__name__)


def config_app_create(app: web.Application, config: ServiceConfig) -> web.Application:
    """
    Create the service configuration from the given YAML file and secrets directory
    """
    app[keys.config] = config

    return app


def metrics_app_create(app: web.Application) -> web.Application:
    """
    Create the metrics registry for the service
    """
    app[keys.metrics] = CollectorRegistry(auto_describe=True)

    return app


def app_init(app: web.Application, config: ServiceConfig):
    """
    Initialize the service with the given configuration file
    This is seperated from service_init as it is also used from the adev dev server
    """

    yaml = YAML()
    # Optional: Configure YAML style (indentation, etc.)
    yaml.indent(mapping=2, sequence=4, offset=2)
    stream = io.StringIO()
    yaml.dump(config.model_dump(mode='json'), stream)

    logger.info(f"CONFIG\n{stream.getvalue()}")

    config_app_create(app, config)
    metrics_app_create(app)
    hams_app_create(app, config.hams)
    mcp_app_create(app, config)
    langgraph_app_create(app, config)

    # Add basic health endpoint to main app at root and prefixed
    from .main import health_check, auth_middleware
    raw_prefix = ""
    if getattr(config.webservice, "prefix", None):
        raw_prefix = config.webservice.prefix
    elif config.webservice.url.path and config.webservice.url.path != "/":
        raw_prefix = config.webservice.url.path

    if raw_prefix:
        api_prefix = ("/" + raw_prefix.strip("/")).rstrip("/")
    else:
        api_prefix = "/api/angry-agent/v1"

    app.router.add_get("/health", health_check)
    if api_prefix != "" and api_prefix != "/health":
        app.router.add_get(f"{api_prefix}/health", health_check)

    # Add middleware for CORS and auth
    app.middlewares.append(auth_middleware)

    return app


def langgraph_app_create(app: web.Application, config: ServiceConfig) -> web.Application:
    """
    Create LangGraph routes and initialize agent endpoints
    This integrates the LangGraph agent defined in main.py with the modular app structure
    """
    from .main import (
        chat_endpoint, list_threads, get_history, get_visualizations,
        delete_thread, update_thread, get_user_settings, update_user_settings,
        get_agents, create_agent, update_agent, delete_agent,
        on_startup, on_cleanup
    )

    raw_prefix = ""
    if getattr(config.webservice, "prefix", None):
        raw_prefix = config.webservice.prefix
    elif config.webservice.url.path and config.webservice.url.path != "/":
        raw_prefix = config.webservice.url.path

    if raw_prefix:
        api_prefix = ("/" + raw_prefix.strip("/")).rstrip("/")
    else:
        api_prefix = "/api/angry-agent/v1"

    # Helper to register resource routes at a given prefix
    def register_resource_routes(prefix: str):
        app.router.add_post(f"{prefix}/chat", chat_endpoint)
        app.router.add_get(f"{prefix}/threads", list_threads)
        app.router.add_get(f"{prefix}/threads/{{thread_id}}/history", get_history)
        app.router.add_get(f"{prefix}/threads/{{thread_id}}/visualizations", get_visualizations)
        app.router.add_delete(f"{prefix}/threads/{{thread_id}}", delete_thread)
        app.router.add_put(f"{prefix}/threads/{{thread_id}}", update_thread)
        app.router.add_get(f"{prefix}/user/settings", get_user_settings)
        app.router.add_put(f"{prefix}/user/settings", update_user_settings)
        app.router.add_get(f"{prefix}/agents", get_agents)
        app.router.add_post(f"{prefix}/agents", create_agent)
        app.router.add_put(f"{prefix}/agents/{{agent_id}}", update_agent)
        app.router.add_delete(f"{prefix}/agents/{{agent_id}}", delete_agent)

    # Register main configured prefix routes
    register_resource_routes(api_prefix)

    # Backward compatibility: also mount at /api (and url.path if distinct)
    if api_prefix != "/api":
        register_resource_routes("/api")

    url_path = config.webservice.url.path.rstrip("/") if config.webservice.url.path and config.webservice.url.path != "/" else ""
    if url_path:
        url_api_path = f"{url_path}/api"
        if url_api_path != api_prefix and url_api_path != "/api":
            register_resource_routes(url_api_path)

    # Add startup and cleanup handlers
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    logger.info("LangGraph app initialized with chat endpoints")

    return app


def app_start(config: ServiceConfig):
    """
    Start the service with the given configuration file
    """
    app = web.Application()

    app_init(app, config)

    web.run_app(
        app,
        host=str(app[keys.config].webservice.url.host),
        port=app[keys.config].webservice.url.port,
        # TODO: Review the custom logging and replace into config
        access_log_format='%a "%r" %s %b "%{Referer}i" "%{User-Agent}i"',
        access_log=logger,
    )

    logger.info(f"Service stopped")
