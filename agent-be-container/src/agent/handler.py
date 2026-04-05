import logging
import json
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from . import create_agent
from typing import Optional
from contextlib import AsyncExitStack
import asyncio
import uuid
from datetime import datetime, timezone
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from ..database import get_db_pool

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self, db_dsn: str, service_config=None, main_llm=None, packager_llm=None, main_prompt: str = "", packager_prompt: str = ""):
        self.db_dsn = db_dsn
        self.service_config = service_config
        self.main_prompt = main_prompt
        self.packager_prompt = packager_prompt

        if main_llm is None:
            main_llm = FakeListChatModel(responses=["I am a placeholder LLM. Please configure a real model."])
        self.main_llm = main_llm

        if packager_llm is None:
            packager_llm = FakeListChatModel(responses=["I am a placeholder LLM. Please configure a real model."])
        self.packager_llm = packager_llm

        self.checkpointer: Optional[AsyncPostgresSaver] = None
        self.agent = None
        self._exit_stack = AsyncExitStack()
        self._background_tasks = set()

    async def initialize(self):
        """Initializes the checkpointer and compiles the agent exactly once."""
        logger.info("Initializing LLMHandler checkpointer and compiling LangGraph agent.")

        pool_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        }

        pool = AsyncConnectionPool(
            conninfo=self.db_dsn,
            max_size=20,
            kwargs=pool_kwargs,
            check=AsyncConnectionPool.check_connection
        )
        await self._exit_stack.enter_async_context(pool)
        self.checkpointer = AsyncPostgresSaver(pool)
        await self.checkpointer.setup()
        self.agent = create_agent(self.main_llm, self.packager_llm, self.main_prompt, self.packager_prompt, self.checkpointer)


    # async def chat(self, thread_id: str, message: str) -> str:
    #     """Invokes the chat agent with the given message."""
    #     if not self.agent:
    #         raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

    #     agent_config = {"configurable": {"thread_id": thread_id}}
    #     final_res = await self.agent.ainvoke({"messages": [HumanMessage(content=message)]}, config=agent_config)

    async def chat_async(self, thread_id: str, message: str) -> None:
        """Starts the chat agent in the background."""
        if not self.agent:
            raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

        agent_config = {
            "configurable": {
                "thread_id": thread_id,
                "service_config": self.service_config
            }
        }

        msg = HumanMessage(
            content=message,
            id=str(uuid.uuid4()),
            additional_kwargs={"timestamp": datetime.now(timezone.utc).isoformat()}
        )

        # Store the human message in the state immediately before starting background task
        # This ensures that history calls find the message even if the graph hasn't started yet.
        # We specify as_node="initial" to avoid "Ambiguous update" errors when manual updates are made.
        await self.agent.aupdate_state(agent_config, {"messages": [msg]}, as_node="initial")

        async def _run_graph():

            async def _set_status(status_msg: str | None):
                try:
                    pool = await get_db_pool()
                    async with pool.acquire() as conn:
                        await conn.execute("UPDATE threads SET status_msg = $1 WHERE thread_id = $2", status_msg, thread_id)
                except Exception as e:
                    logger.error(f"Failed to update status_msg for thread {thread_id}: {e}", exc_info=False)

            try:
                # Use astream_events with the message to trigger the graph.
                # De-duplication is handled by the 'add_messages' reducer because we use a fixed ID.
                # version="v2" is the current standard for LangChain streaming
                async for event in self.agent.astream_events({"messages": [msg]}, config=agent_config, version="v2"):
                    kind = event["event"]
                    name = event.get("name", "unknown")

                    if kind == "on_chain_start":
                        if name == "LangGraph":
                            logger.info(f"Thread {thread_id}: LangGraph execution started.")
                            await _set_status("Agent starting up...")
                        else:
                            logger.info(f"Thread {thread_id}: Node '{name}' started.")
                            await _set_status(f"Running: {name}...")
                    elif kind == "on_chain_end":
                        if name == "LangGraph":
                            logger.info(f"Thread {thread_id}: LangGraph execution finished.")
                        else:
                            logger.info(f"Thread {thread_id}: Node '{name}' finished.")
                    elif kind == "on_tool_start":
                        logger.info(f"Thread {thread_id}: Tool '{name}' started executing.")
                        await _set_status(f"Executing tool: {name}...")
                    elif kind == "on_tool_end":
                        logger.info(f"Thread {thread_id}: Tool '{name}' finished executing.")

            except Exception as e:
                logger.error(f"Error in background task for thread {thread_id}: {e}", exc_info=True)
                err_msg = AIMessage(content=f"Oops! I encountered an error: {str(e)}", id=str(uuid.uuid4()))
                await self.agent.aupdate_state(agent_config, {"messages": [err_msg]}, as_node="initial")
            finally:
                try:
                    pool = await get_db_pool()
                    async with pool.acquire() as conn:
                        await conn.execute("UPDATE threads SET locked_until = NULL, status_msg = NULL WHERE thread_id = $1", thread_id)
                except Exception as e:
                    logger.error(f"Failed to release lock and status for thread {thread_id}: {e}", exc_info=True)

        task = asyncio.create_task(_run_graph())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


    async def get_thread_state(self, thread_id: str) -> dict:
        """Retrieves the full discrete state for a given thread."""
        if not self.agent:
            raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

        agent_config = {
            "configurable": {
                "thread_id": thread_id,
                "service_config": self.service_config
            }
        }
        state = await self.agent.aget_state(agent_config)
        return state


    async def close(self):
        """Closes the checkpointer resources."""
        await self._exit_stack.aclose()
