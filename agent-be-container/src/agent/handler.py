import logging
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from . import create_agent
from typing import Optional
from contextlib import AsyncExitStack
import asyncio

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self, db_dsn: str, llm=None):
        self.db_dsn = db_dsn
        if llm is None:
            from langchain_core.language_models.fake_chat_models import FakeListChatModel
            llm = FakeListChatModel(responses=["I am a placeholder LLM. Please configure a real model."])
        self.llm = llm
        self.checkpointer: Optional[AsyncPostgresSaver] = None
        self.agent = None
        self._exit_stack = AsyncExitStack()
        self._background_tasks = set()

    async def initialize(self):
        """Initializes the checkpointer and compiles the agent exactly once."""
        logger.info("Initializing LLMHandler checkpointer and compiling LangGraph agent.")
        self.checkpointer = await self._exit_stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(self.db_dsn)
        )
        await self.checkpointer.setup()
        self.agent = create_agent(self.llm, self.checkpointer)


    async def chat(self, thread_id: str, message: str) -> str:
        """Invokes the chat agent with the given message."""
        if not self.agent:
            raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

        agent_config = {"configurable": {"thread_id": thread_id}}
        final_res = await self.agent.ainvoke({"messages": [HumanMessage(content=message)]}, config=agent_config)

        messages = final_res.get("messages", [])
        last_msg = messages[-1] if messages else None
        return last_msg.content if last_msg else ""

    async def chat_async(self, thread_id: str, message: str) -> None:
        """Starts the chat agent in the background."""
        if not self.agent:
            raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

        agent_config = {"configurable": {"thread_id": thread_id}}

        import uuid
        msg = HumanMessage(content=message, id=str(uuid.uuid4()))

        async def _run_graph():
            try:
                await self.agent.ainvoke({"messages": [msg]}, config=agent_config)
            except Exception as e:
                logger.error(f"Error in background task for thread {thread_id}: {e}", exc_info=True)
                err_msg = AIMessage(content=f"Oops! I encountered an error: {str(e)}", id=str(uuid.uuid4()))
                await self.agent.aupdate_state(agent_config, {"messages": [err_msg]})

        task = asyncio.create_task(_run_graph())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


    async def get_thread_state(self, thread_id: str) -> dict:
        """Retrieves the full discrete state for a given thread."""
        if not self.agent:
            raise RuntimeError("LLMHandler is not initialized. Call initialize() first.")

        agent_config = {"configurable": {"thread_id": thread_id}}
        state = await self.agent.aget_state(agent_config)
        return state


    async def close(self):
        """Closes the checkpointer resources."""
        await self._exit_stack.aclose()
