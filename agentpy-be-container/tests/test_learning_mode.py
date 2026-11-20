import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
import sys
import os
import asyncio

# Add container root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agent import create_agent
from src.agent.handler import LLMHandler
from src.agent.structs import PromptFeedback

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="LLM Response"))
    
    # Mock with_structured_output for different schemas
    def side_effect(schema, **kwargs):
        mock = MagicMock()
        if schema == PromptFeedback:
            mock.ainvoke = AsyncMock(return_value={
                "parsed": PromptFeedback(
                    feedback_text="Good prompt",
                    improved_prompt="Better prompt",
                    alternatives=["Alt 1"]
                ),
                "raw": MagicMock(usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30})
            })
        else:
            # Follow-up questions or others
            mock.ainvoke = AsyncMock(return_value={
                "parsed": MagicMock(follow_up_questions=["Q1", "Q2", "Q3"]),
                "raw": MagicMock(usage_metadata={"input_tokens": 5, "output_tokens": 5, "total_tokens": 10})
            })
        return mock
    
    llm.with_structured_output.side_effect = side_effect
    return llm

@pytest.mark.asyncio
async def test_learning_mode_trigger(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
    
    # Enable learning mode in state
    config = {"configurable": {"thread_id": "test-learning"}}
    await agent.aupdate_state(config, {"learning_mode_enabled": True})
    
    # Send a message
    input_msg = HumanMessage(content="Analyze this")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    
    # Should have triggered learning mode feedback (the last message should be from learning_mode_node)
    # Looking at agent/__init__.py, learning_mode_node returns an AIMessage with learning_mode_feedback in additional_kwargs
    messages = result["messages"]
    last_msg = messages[-1]
    
    assert "learning_mode_feedback" in last_msg.additional_kwargs
    assert last_msg.additional_kwargs["learning_mode_feedback"]["feedback_text"] == "Good prompt"

@pytest.mark.asyncio
async def test_learning_mode_bypass(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
    
    # Enable learning mode in state
    config = {"configurable": {"thread_id": "test-bypass"}}
    await agent.aupdate_state(config, {"learning_mode_enabled": True})
    
    # Send a message with bypass flag
    input_msg = HumanMessage(
        content="Direct work",
        additional_kwargs={"learning_mode_bypass": True}
    )
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    
    # Should have bypassed learning mode and gone to LLM
    messages = result["messages"]
    last_msg = messages[-1]
    
    # AIMessage from LLM node should not have learning_mode_feedback (unless we added it which we didn't)
    assert "learning_mode_feedback" not in last_msg.additional_kwargs
    assert last_msg.content == "LLM Response"

@pytest.mark.asyncio
@patch("src.agent.handler.get_db_pool", new_callable=AsyncMock)
async def test_handler_passes_bypass_flag(mock_get_pool, mock_llm):
    # Mock DB pool for the internal background tasks
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_get_pool.return_value = mock_pool
    
    # We create the handler but DO NOT call initialize() to avoid real DB connections/pools
    handler = LLMHandler(db_dsn="postgresql://localhost/fake", main_llm=mock_llm, packager_llm=mock_llm)
    
    # Create the agent with MemorySaver for testing
    handler.agent = create_agent(mock_llm, mock_llm, checkpointer=MemorySaver())
    
    # Enable learning mode in state for this thread
    thread_id = "test-thread"
    config = {"configurable": {"thread_id": thread_id}}
    await handler.agent.aupdate_state(config, {"learning_mode_enabled": True}, as_node="initial")
    
    # Call chat_async with bypass_learning_mode=True
    # Note: chat_async runs in a background task
    await handler.chat_async(thread_id, "Use suggestion", bypass_learning_mode=True)
    
    # Wait for the background task to run. 
    # Increased wait time to 1s to be safer in Docker environments.
    await asyncio.sleep(1.0)
    
    # Check the state
    state = await handler.get_thread_state(thread_id)
    messages = state.values["messages"]
    
    # Filter for human messages
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_msgs) > 0
    assert human_msgs[-1].additional_kwargs.get("learning_mode_bypass") is True
    
    # Filter for AI messages
    ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
    assert len(ai_msgs) > 0
    
    # The response should be from LLM node, not feedback
    # (In our mock, LLM response doesn't have learning_mode_feedback)
    found_feedback = any("learning_mode_feedback" in m.additional_kwargs for m in ai_msgs)
    assert found_feedback is False
    assert any(m.content == "LLM Response" for m in ai_msgs)
