import os
import warnings
# Suppress Pydantic V1 warning on Python 3.14 until langchain-core updates
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*")

import logging
import uuid
import json
from aiohttp import web
from langchain_core.messages import HumanMessage
from .agent import create_agent
from .agent.handler import LLMHandler
from .database import init_db_pool, close_db_pool, get_db_pool, create_tables
from . import keys


from .config import ServiceConfig

# Config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def auth_middleware(app, handler):
    async def middleware_handler(request):
        # Handle CORS preflight
        if request.method == "OPTIONS":
            response = web.Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-User-ID"
            return response

        # Allow health check without auth
        if request.path == "/health":
            return await handler(request)

        # Default to a test user if header matches request from single-user UI
        # or just allow it for now since we are removing login.
        user_id = request.headers.get("X-User-ID")
        if not user_id:
             # Fallback for single user mode if header is missing (though frontend should send it)
             user_id = "default-user"

        request["user_id"] = user_id

        try:
            response = await handler(request)
        except Exception as e:
             logger.error(f"Error handling request: {e}", exc_info=True)
             response = web.json_response({"error": str(e)}, status=500)

        # Always add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    return middleware_handler

async def health_check(request):
    return web.json_response({"status": "ok"})

async def chat_endpoint(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    try:
        data = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    message = data.get("message")
    thread_id = data.get("thread_id")

    if not message:
        return web.json_response({"error": "Message required"}, status=400)

    if not thread_id:
        thread_id = str(uuid.uuid4())

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)
        if row:
            if row["user_id"] != user_id:
                return web.json_response({"error": "Thread access denied"}, status=403)
        else:
            await conn.execute(
                "INSERT INTO threads (thread_id, user_id, title) VALUES ($1, $2, $3)",
                thread_id, user_id, message[:30]
            )

    # --- Agent Logic ---
    llm_handler: LLMHandler = request.app["llm_handler"]
    await llm_handler.chat_async(thread_id, message)

    return web.json_response(
        {
            "thread_id": thread_id,
            "status": "processing"
        },
        status=202
    )

async def list_threads(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    threads = []

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT thread_id, title, color, created_at FROM threads WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        threads = [dict(r) for r in rows]
        for t in threads:
            if t.get("created_at"): t["created_at"] = str(t["created_at"])

    return web.json_response({"threads": threads})

async def get_history(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id, color FROM threads WHERE thread_id = $1", thread_id)
        if not row or row["user_id"] != user_id:
            return web.json_response({"error": "Not found"}, status=404)

    llm_handler: LLMHandler = request.app["llm_handler"]
    state = await llm_handler.get_thread_state(thread_id)
    messages_list = []
    if state.values and "messages" in state.values:
        for m in state.values["messages"]:
            messages_list.append({"type": m.type, "content": m.content})
    return web.json_response({
            "thread": {"thread_id": thread_id, "user_id": row["user_id"], "color": row["color"]},
            "messages": messages_list
        })

async def delete_thread(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check ownership
        row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)
        if not row or row["user_id"] != user_id:
             return web.json_response({"error": "Not found or access denied"}, status=404)

        # Delete thread metadata
        await conn.execute("DELETE FROM threads WHERE thread_id = $1", thread_id)

        # Note: We are not cleaning up checkpoints in Postgres for now as it requires complex query on bytea/blob
        # In a real app we'd want to clean that up too.

        return web.json_response({"status": "deleted"})

async def update_thread_color(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    try:
        data = await request.json()
        color = data.get("color")
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)
        if not row or row["user_id"] != user_id:
             return web.json_response({"error": "Not found or access denied"}, status=404)
        await conn.execute("UPDATE threads SET color = $1, updated_at = NOW() WHERE thread_id = $2", color, thread_id)
        return web.json_response({"status": "updated"})

async def on_startup(app):
    config: ServiceConfig = app[keys.config]
    logger.info("Starting up and connecting to DB...")
    try:
        pool = await init_db_pool(config.persistence.db)
        if config.persistence.db.automigrate:
            async with pool.acquire() as conn:
                await create_tables(conn)

        # Initialize LLM
        logger.info("Initializing LLM")
        from .agent import llm_model
        llm = llm_model(config.aiclient)

        # Initialize LLM Handler
        logger.info("Initializing LLMHandler")
        llm_handler = LLMHandler(db_dsn=config.persistence.db.connection.dsn, llm=llm)
        await llm_handler.initialize()
        app["llm_handler"] = llm_handler

        logger.info("DB initialized.")
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")
        raise e

async def on_cleanup(app):
    logger.info("Cleaning up...")
    llm_handler = app.get("llm_handler")
    if llm_handler:
        await llm_handler.close()
    await close_db_pool()

def create_app_with_middleware(config: ServiceConfig):
    """
    Create app with middleware - used when main.py runs standalone
    This is mostly for backward compatibility, the preferred way is via __init__.py
    """
    app = web.Application(middlewares=[auth_middleware])
    app[keys.config] = config
    app.router.add_get("/health", health_check)
    app.router.add_post("/api/chat", chat_endpoint)
    app.router.add_get("/api/threads", list_threads)
    app.router.add_get("/api/threads/{thread_id}/history", get_history)
    app.router.add_delete("/api/threads/{thread_id}", delete_thread)
    app.router.add_patch("/api/threads/{thread_id}/color", update_thread_color)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

def app_start(config: ServiceConfig):
    """Start the service - used by CLI"""
    app = create_app_with_middleware(config)
    web.run_app(app,
                host=str(config.webservice.url.host) if config.webservice.url.host else "0.0.0.0",
                port=config.webservice.url.port or 8080)

if __name__ == "__main__":
    # Fallback to defaults if run directly without config
    # This might fail if ServiceConfig requires params, but we can try basic defaults
    # Or just warn.
    print("Please run via cli.py to support full configuration")
    # Minimal config for direct run (e.g. dev)
    # We can try to load via Env or defaults
    try:
        config = ServiceConfig(
            webservice={"url": "http://0.0.0.0:8080", "prefix": ""},
            persistence={
                "db": {
                    "pool_size": 10,
                    "automigrate": True,
                    "acquire_timeout": 10,
                    "connection": {
                        "url": "postgresql://localhost:5432/agentdb",
                        "username": "postgres",
                        "password": "mysecretpassword"
                    }
                }
            }
        )
        app_start(config)
    except Exception as e:
        print(f"Failed to start with default config: {e}")
