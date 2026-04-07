import os
import warnings
# Suppress Pydantic V1 warning on Python 3.14 until langchain-core updates
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*")

import logging
import uuid
import json
import jwt
from aiohttp import web
from langchain_core.messages import HumanMessage
from .agent import create_agent
from .agent.handler import LLMHandler
from .database import init_db_pool, close_db_pool, get_db_pool
from . import keys
from datetime import datetime, timezone


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
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-User-ID, Authorization"
            return response

        # Allow health check without auth (handle prefixed case as well)
        if request.path.endswith("/health"):
            return await handler(request)

        user_id = None
        user_name = None

        # Try extracting user_id from Authorization Header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:] # remove 'Bearer '
            try:
                decoded_payload = jwt.decode(token, options={"verify_signature": False})
                # Check standard claims
                user_id = decoded_payload.get("sub") or decoded_payload.get("user_id") or decoded_payload.get("preferred_username")
                if not user_id:
                    # If standard claims are missing, serialize payload as a fallback identifier or fallback to default
                    user_id = "default-user"
                    logger.warning(f"JWT decoded but no 'sub' or 'user_id' claim found. Payload: {decoded_payload}")

                # Extract user_name for tracking logins
                user_name = decoded_payload.get("name") or decoded_payload.get("preferred_username") or decoded_payload.get("email")
            except Exception as e:
                logger.error(f"Failed to decode JWT: {e}")

        # Fallback to X-User-ID header
        if not user_id:
            user_id = request.headers.get("X-User-ID")

        if not user_id:
             # Fallback for single user mode if header is missing
             user_id = "default-user"
        if not user_name:
            user_name = user_id

        request["user_id"] = user_id
        request["user_name"] = user_name

        try:
            response = await handler(request)
        except web.HTTPException:
            # Let aiohttp handle its own exceptions (404, etc.)
            raise
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
    bypass_learning_mode = data.get("bypass_learning_mode", False)

    if not message:
        return web.json_response({"error": "Message required"}, status=400)

    if not thread_id:
        thread_id = str(uuid.uuid4())

    pool = await get_db_pool()
    llm_handler: LLMHandler = request.app["llm_handler"]

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)

        is_new_thread = False

        if row:
            if row["user_id"] != user_id:
                # Check thread_access table for additional users
                access_row = await conn.fetchrow("SELECT 1 FROM thread_access WHERE thread_id = $1 AND user_id = $2", thread_id, user_id)
                if not access_row:
                    return web.json_response({"error": "Thread access denied"}, status=403)
        else:
            is_new_thread = True
            await conn.execute(
                "INSERT INTO threads (thread_id, user_id, title) VALUES ($1, $2, $3)",
                thread_id, user_id, message[:30]
            )

        # Attempt to acquire the lock
        lock_query = """
            UPDATE threads
            SET locked_until = NOW() + INTERVAL '5 minutes'
            WHERE thread_id = $1 AND (locked_until IS NULL OR locked_until < NOW())
            RETURNING thread_id;
        """
        locked_row = await conn.fetchrow(lock_query, thread_id)
        if not locked_row:
            return web.json_response({"error": "Thread is busy processing a previous request."}, status=409)

    # For new threads, initialize the state with the user's default learning mode setting
    if is_new_thread:
        async with pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT learning_mode_enabled FROM users WHERE user_id = $1", user_id)
            user_learning_mode = user_row["learning_mode_enabled"] if user_row else False

        # Initialize state with the default setting
        agent_config = {
            "configurable": {
                "thread_id": thread_id,
                "service_config": config
            }
        }
        await llm_handler.agent.aupdate_state(agent_config, {"learning_mode_enabled": user_learning_mode}, as_node="initial")


    # --- Agent Logic ---
    await llm_handler.chat_async(thread_id, message, bypass_learning_mode)

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
    user_name = request["user_name"]

    threads = []

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Update user tracking information
        await conn.execute(
            """
            INSERT INTO users (user_id, user_name, last_login_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET user_name = EXCLUDED.user_name,
                last_login_at = NOW()
            """,
            user_id, user_name
        )

        query = """
            SELECT DISTINCT t.thread_id, t.title, t.color, t.created_at
            FROM threads t
            LEFT JOIN thread_access ta ON t.thread_id = ta.thread_id
            WHERE t.user_id = $1 OR ta.user_id = $1
            ORDER BY t.created_at DESC
        """
        rows = await conn.fetch(query, user_id)
        threads = [dict(r) for r in rows]
        for t in threads:
            if t.get("created_at"): t["created_at"] = str(t["created_at"])

    return web.json_response({"threads": threads})

from src.agent.agent_store import get_all_agent_definitions, save_agent_definition, delete_agent_definition

async def get_agents(request: web.Request) -> web.Response:
    try:
        agents = await get_all_agent_definitions()
        return web.json_response(agents)
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def create_agent(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        name = data.get('name')
        content = data.get('content')
        if not name or not content:
            return web.json_response({"error": "name and content are required"}, status=400)

        config: ServiceConfig = request.app[keys.config]
        agent_id = await save_agent_definition(name, content, config)
        return web.json_response({"id": agent_id, "name": name, "content": content}, status=201)
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def update_agent(request: web.Request) -> web.Response:
    agent_id = request.match_info.get('agent_id')
    if not agent_id:
        return web.json_response({"error": "agent_id is required"}, status=400)

    try:
        data = await request.json()
        name = data.get('name')
        content = data.get('content')
        if not name or not content:
            return web.json_response({"error": "name and content are required"}, status=400)

        config: ServiceConfig = request.app[keys.config]
        await save_agent_definition(name, content, config, agent_id=agent_id)
        return web.json_response({"id": agent_id, "name": name, "content": content})
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def delete_agent(request: web.Request) -> web.Response:
    agent_id = request.match_info.get('agent_id')
    if not agent_id:
        return web.json_response({"error": "agent_id is required"}, status=400)

    try:
        await delete_agent_definition(agent_id)
        return web.json_response({"status": "deleted"})
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def get_user_settings(request):
    user_id = request["user_id"]
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT learning_mode_enabled FROM users WHERE user_id = $1", user_id)
        if not row:
             return web.json_response({"learning_mode_enabled": False})
        return web.json_response({"learning_mode_enabled": bool(row["learning_mode_enabled"])})

async def update_user_settings(request):
    user_id = request["user_id"]
    try:
        data = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    learning_mode_enabled = data.get("learning_mode_enabled")
    if learning_mode_enabled is None:
        return web.json_response({"error": "Missing 'learning_mode_enabled'"}, status=400)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, learning_mode_enabled)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET learning_mode_enabled = EXCLUDED.learning_mode_enabled
            """,
            user_id, learning_mode_enabled
        )
    return web.json_response({"status": "updated"})

async def get_history(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id, color, status_msg, status_updated_at FROM threads WHERE thread_id = $1", thread_id)
        if not row:
            return web.json_response({"thread": {"thread_id": thread_id}, "messages": []})

        if row["user_id"] != user_id:
            access_row = await conn.fetchrow("SELECT 1 FROM thread_access WHERE thread_id = $1 AND user_id = $2", thread_id, user_id)
            if not access_row:
                return web.json_response({"thread": {"thread_id": thread_id}, "messages": []})

    llm_handler: LLMHandler = request.app["llm_handler"]
    state = await llm_handler.get_thread_state(thread_id)
    messages_list = []
    max_tokens = getattr(config.main_aiclient, "context_length", None)

    if state.values and "messages" in state.values:
        last_human_timestamp = None
        ai_msg_with_tools = None

        for m in state.values["messages"]:
            msg_dict = {"type": m.type, "content": getattr(m, "content", "")}

            if hasattr(m, "name") and m.name:
                msg_dict["name"] = m.name

            if m.type == "tool":
                tool_call_id = getattr(m, "tool_call_id", None)
                if tool_call_id:
                    msg_dict["tool_call_id"] = tool_call_id

            msg_timestamp = None

            if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                if "timestamp" in m.additional_kwargs:
                    msg_timestamp = m.additional_kwargs["timestamp"]
                    msg_dict["created_at"] = msg_timestamp
                msg_dict["additional_kwargs"] = m.additional_kwargs

            if m.type == "ai" and hasattr(m, "tool_calls") and m.tool_calls:
                tool_calls = []
                for tc in m.tool_calls:
                    tc_dict = {
                        "id": tc.get("id"),
                        "name": tc.get("name", "Unknown Tool"),
                        "args": tc.get("args", {})
                    }
                    tool_calls.append(tc_dict)

                if "additional_kwargs" not in msg_dict:
                    msg_dict["additional_kwargs"] = {}
                msg_dict["additional_kwargs"]["tool_calls"] = tool_calls

            if m.type == "human" and msg_timestamp:
                try:
                    last_human_timestamp = datetime.fromisoformat(msg_timestamp.replace('Z', '+00:00'))
                except ValueError:
                    pass
            elif m.type in ("ai", "error") and msg_timestamp and last_human_timestamp:
                try:
                    ai_timestamp = datetime.fromisoformat(msg_timestamp.replace('Z', '+00:00'))
                    duration_sec = (ai_timestamp - last_human_timestamp).total_seconds()
                    if duration_sec > 0:
                        msg_dict["duration"] = f"{int(duration_sec)}s"
                except ValueError:
                    pass

            if hasattr(m, 'usage_metadata') and m.usage_metadata:
                usage = dict(m.usage_metadata)
                if max_tokens:
                    usage["max_tokens"] = max_tokens
                msg_dict["usage_metadata"] = usage

            messages_list.append(msg_dict)
    visualizations_list = []
    if state.values and "visualizations" in state.values:
        for v in state.values["visualizations"]:
            v_dict = v.model_dump()
            visualizations_list.append(v_dict)

    return web.json_response({
            "thread": {
                "thread_id": thread_id,
                "user_id": row["user_id"],
                "color": row["color"],
                "status_msg": row["status_msg"],
                "status_updated_at": str(row["status_updated_at"]) if row["status_updated_at"] else None,
                "current_server_time": datetime.now(timezone.utc).isoformat(),
                "learning_mode_enabled": bool(state.values.get("learning_mode_enabled", False)) if state and state.values else False
            },
            "messages": messages_list,
            "visualizations": visualizations_list
        })

async def delete_thread(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Delete thread metadata atomically checking ownership
        result = await conn.execute("DELETE FROM threads WHERE thread_id = $1 AND user_id = $2", thread_id, user_id)

        # conn.execute returns a string like 'DELETE 1' or 'DELETE 0'
        if result == "DELETE 0":
             return web.json_response({"error": "Not found or access denied"}, status=404)

        # Note: We are not cleaning up checkpoints in Postgres for now as it requires complex query on bytea/blob
        # In a real app we'd want to clean that up too.

        return web.json_response({"status": "deleted"})

async def update_thread(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    try:
        data = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    color = data.get("color")
    title = data.get("title")

    # Require both fields for a full update (PUT semantic)
    if color is None or title is None:
        return web.json_response({"error": "Missing 'color' or 'title' in request body"}, status=400)

    learning_mode_enabled = data.get("learning_mode_enabled")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        query = """
            UPDATE threads
            SET color = $1, title = $2, updated_at = NOW()
            WHERE thread_id = $3 AND user_id = $4
        """
        result = await conn.execute(query, color, title, thread_id, user_id)

        # conn.execute returns a string like 'UPDATE 1' or 'UPDATE 0'
        if result == "UPDATE 0":
            return web.json_response({"error": "Not found or access denied"}, status=404)

    if learning_mode_enabled is not None:
        llm_handler: LLMHandler = request.app["llm_handler"]
        agent_config = {
            "configurable": {
                "thread_id": thread_id,
                "service_config": config
            }
        }
        await llm_handler.agent.aupdate_state(agent_config, {"learning_mode_enabled": learning_mode_enabled}, as_node="initial")

    return web.json_response({"status": "updated"})

async def get_visualizations(request):
    config: ServiceConfig = request.app[keys.config]
    user_id = request["user_id"]
    thread_id = request.match_info["thread_id"]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # First check if the user has access to this thread
        row = await conn.fetchrow("SELECT user_id FROM threads WHERE thread_id = $1", thread_id)
        if not row:
            return web.json_response({"visualizations": []})

        if row["user_id"] != user_id:
            access_row = await conn.fetchrow("SELECT 1 FROM thread_access WHERE thread_id = $1 AND user_id = $2", thread_id, user_id)
            if not access_row:
                return web.json_response({"visualizations": []})

    llm_handler: LLMHandler = request.app["llm_handler"]
    state = await llm_handler.get_thread_state(thread_id)
    visualizations_list = []
    if state.values and "visualizations" in state.values:
        for v in state.values["visualizations"]:
            visualizations_list.append(v.model_dump())

    return web.json_response({"visualizations": visualizations_list})

async def on_startup(app):
    config: ServiceConfig = app[keys.config]
    logger.info("Starting up and connecting to DB...")
    try:
        if config.persistence.db.automigrate:
            logger.info("Running database migrations...")
            from yoyo import read_migrations, get_backend
            import os

            backend = get_backend(config.persistence.db.connection.dsn)
            migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
            migrations = read_migrations(migrations_dir)

            with backend.lock():
                backend.apply_migrations(backend.to_apply(migrations))
            logger.info("Database migrations applied.")

        pool = await init_db_pool(config.persistence.db)

        # Initialize LLM
        logger.info("Initializing LLM")
        from .agent import llm_model
        main_llm = llm_model(config.main_aiclient)
        packager_llm = llm_model(config.packager_aiclient)

        main_prompt = config.main_aiclient.system_prompt or ""
        packager_prompt = config.packager_aiclient.system_prompt or ""

        # Initialize LLM Handler
        logger.info("Initializing LLMHandler")
        llm_handler = LLMHandler(
            db_dsn=config.persistence.db.connection.dsn,
            service_config=config,
            main_llm=main_llm,
            packager_llm=packager_llm,
            main_prompt=main_prompt,
            packager_prompt=packager_prompt
        )
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
    path_prefix = config.webservice.url.path if config.webservice.url.path and config.webservice.url.path != "/" else ""
    path_prefix = path_prefix.rstrip("/")

    app.router.add_get(f"{path_prefix}/health", health_check)
    app.router.add_post(f"{path_prefix}/api/chat", chat_endpoint)
    app.router.add_get(f"{path_prefix}/api/threads", list_threads)
    app.router.add_get(f"{path_prefix}/api/threads/{{thread_id}}/history", get_history)
    app.router.add_get(f"{path_prefix}/api/threads/{{thread_id}}/visualizations", get_visualizations)

    app.router.add_delete(f"{path_prefix}/api/threads/{{thread_id}}", delete_thread)
    app.router.add_put(f"{path_prefix}/api/threads/{{thread_id}}", update_thread)

    app.router.add_get(f"{path_prefix}/api/user/settings", get_user_settings)
    app.router.add_put(f"{path_prefix}/api/user/settings", update_user_settings)

    app.router.add_get(f"{path_prefix}/api/agents", get_agents)
    app.router.add_post(f"{path_prefix}/api/agents", create_agent)
    app.router.add_put(f"{path_prefix}/api/agents/{{agent_id}}", update_agent)
    app.router.add_delete(f"{path_prefix}/api/agents/{{agent_id}}", delete_agent)

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
            },
            main_aiclient={
                "model_provider": "google_genai",
                "context_length": 8192,
                "google_api_key": "dummy"
            },
            packager_aiclient={
                "model_provider": "google_genai",
                "context_length": 8192,
                "google_api_key": "dummy"
            },
            embedding_client={
                "model_provider": "google_genai",
                "model": "text-embedding-004",
                "google_api_key": "dummy"
            }
        )
        app_start(config)
    except Exception as e:
        print(f"Failed to start with default config: {e}")
