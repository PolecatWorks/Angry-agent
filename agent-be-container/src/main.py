import os
import warnings
# Suppress Pydantic V1 warning on Python 3.14 until langchain-core updates
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*")

import logging
import uuid
import json
from aiohttp import web
from langchain_core.messages import HumanMessage
from agent import create_agent
from database import init_db_pool, close_db_pool, get_db_pool, create_tables, DSN

# Optional imports for NO_DB mode
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    MemorySaver = None

from .config import ServiceConfig

# Config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Data
mock_threads_db = {}
mock_checkpointer = MemorySaver() if MemorySaver else None

async def auth_middleware(app, handler):
    async def middleware_handler(request):
        # Handle CORS preflight
        if request.method == "OPTIONS":
            response = web.Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
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
    config: ServiceConfig = request.app["config"]
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

    # --- DB Logic: Threads Table ---
    if config.no_db:
        if thread_id not in mock_threads_db:
            mock_threads_db[thread_id] = {"user_id": user_id, "title": message[:20], "thread_id": thread_id}
        elif mock_threads_db[thread_id]["user_id"] != user_id:
             return web.json_response({"error": "Thread access denied"}, status=403)
    else:
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
    agent_config = {"configurable": {"thread_id": thread_id}}
    final_res = {}

    if config.no_db:
        agent = create_agent(mock_checkpointer)
        final_res = await agent.ainvoke({"messages": [HumanMessage(content=message)]}, config=agent_config)
    else:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(config.database.dsn) as checkpointer:
            # Ensure checkpointer tables exist
            await checkpointer.setup()
            agent = create_agent(checkpointer)
            final_res = await agent.ainvoke({"messages": [HumanMessage(content=message)]}, config=agent_config)

    messages = final_res["messages"]
    last_msg = messages[-1]
    response_text = last_msg.content if last_msg else ""

    return web.json_response({
        "thread_id": thread_id,
        "response": response_text
    })

async def list_threads(request):
    config: ServiceConfig = request.app["config"]
    user_id = request["user_id"]
    threads = []

    if config.no_db:
        for tid, data in mock_threads_db.items():
            if data["user_id"] == user_id:
                threads.append(data)
    else:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT thread_id, title, created_at FROM threads WHERE user_id = $1 ORDER BY updated_at DESC", user_id)
            threads = [dict(r) for r in rows]
            for t in threads:
                if t.get("created_at"): t["created_at"] = str(t["created_at"])

    return web.json_response({"threads": threads})

async def get_history(request):
    config: ServiceConfig = request.app["config"]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    if config.no_db:
        if thread_id not in mock_threads_db or mock_threads_db[thread_id]["user_id"] != user_id:
             return web.json_response({"error": "Not found"}, status=404)
        checkpointer = mock_checkpointer # Reuse global mock

        # Check if we need to "construct" agent to get state
        agent = create_agent(checkpointer)
        agent_config = {"configurable": {"thread_id": thread_id}}
        state = await agent.aget_state(agent_config)
        messages_list = []
        if state.values and "messages" in state.values:
             for m in state.values["messages"]:
                messages_list.append({"type": m.type, "content": m.content})
        return web.json_response({"messages": messages_list})

    else:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)
            if not row or row["user_id"] != user_id:
                return web.json_response({"error": "Not found"}, status=404)

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(config.database.dsn) as checkpointer:
            agent = create_agent(checkpointer)
            agent_config = {"configurable": {"thread_id": thread_id}}
            state = await agent.aget_state(agent_config)
            messages_list = []
            if state.values and "messages" in state.values:
                for m in state.values["messages"]:
                    messages_list.append({"type": m.type, "content": m.content})
            return web.json_response({"messages": messages_list})

async def on_startup(app):
    config: ServiceConfig = app["config"]
    if config.no_db:
        logger.info("Skipping DB init due to NO_DB config")
        return

    logger.info("Starting up and connecting to DB...")
    try:
        pool = await init_db_pool(dsn=config.database.dsn)
        async with pool.acquire() as conn:
            await create_tables(conn)
        logger.info("DB initialized.")
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")
        raise e

async def on_cleanup(app):
    logger.info("Cleaning up...")
    await close_db_pool()

def create_app(config: ServiceConfig = None):
    if config is None:
        # Fallback for dev/testing when config isn't injected (e.g. adev)
        # We try to load partial config from env or just use defaults
        try:
            # Create a default config.
            # Note: This might miss secrets or yaml if not specified.
            # We assume dev mode defaults are sufficient.
            config = ServiceConfig(webservice={"url": "http://0.0.0.0:8000", "prefix": ""})
            # Attempt to set specific fields from env if needed, but ServiceConfig does that via pydantic if we let it.
            # But here we just instantiated with minimal args.
            pass
        except Exception as e:
            logger.warning(f"Using fallback config failed slightly: {e}")
            config = ServiceConfig(webservice={"url": "http://0.0.0.0:8000", "prefix": ""})

    app = web.Application(middlewares=[auth_middleware])
    app["config"] = config
    app.router.add_get("/health", health_check)
    app.router.add_post("/api/chat", chat_endpoint)
    app.router.add_get("/api/threads", list_threads)
    app.router.add_get("/api/threads/{thread_id}/history", get_history)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

def app_start(config: ServiceConfig):
    app = create_app(config)
    web.run_app(app,
                host=str(config.webservice.url.host) if config.webservice.url.host else "0.0.0.0",
                port=config.webservice.url.port or 8000)

if __name__ == "__main__":
    # Fallback to defaults if run directly without config
    # This might fail if ServiceConfig requires params, but we can try basic defaults
    # Or just warn.
    print("Please run via cli.py to support full configuration")
    # Minimal config for direct run (e.g. dev)
    # We can try to load via Env or defaults
    try:
        config = ServiceConfig(webservice={"url": "http://0.0.0.0:8000", "prefix": ""})
        app_start(config)
    except Exception as e:
        print(f"Failed to start with default config: {e}")
