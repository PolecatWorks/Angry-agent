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

    # Add basic health endpoint to main app
    from .main import health_check, auth_middleware
    app.router.add_get("/health", health_check)

    # Add middleware for CORS and auth
    app.middlewares.append(auth_middleware)

    return app


def langgraph_app_create(app: web.Application, config: ServiceConfig) -> web.Application:
    """
    Create LangGraph routes and initialize agent endpoints
    This integrates the LangGraph agent defined in main.py with the modular app structure
    """
    from .main import chat_endpoint, list_threads, get_history, on_startup, on_cleanup

    # Add API routes for LangGraph agent
    app.router.add_post("/api/chat", chat_endpoint)
    app.router.add_get("/api/threads", list_threads)
    app.router.add_get("/api/threads/{thread_id}/history", get_history)

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
        host=app[keys.config].webservice.url.host,
        port=app[keys.config].webservice.url.port,
        # TODO: Review the custom logging and replace into config
        access_log_format='%a "%r" %s %b "%{Referer}i" "%{User-Agent}i"',
        access_log=logger,
    )

    logger.info(f"Service stopped")
