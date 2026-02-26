"""
Tests for the agent conversation flow
"""
import pytest
from unittest.mock import MagicMock
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent

@pytest.fixture
def mock_llm():
    return FakeListChatModel(responses=["LLM Response"])


@pytest.mark.asyncio
async def test_hello_intent(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-hello"}}

    # Test Hello
    input_msg = HumanMessage(content="Hello world")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "Hello there!"

@pytest.mark.asyncio
async def test_llm_intent(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-llm"}}

    # Test LLM Route
    input_msg = HumanMessage(content="Testing 123")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "LLM Response"

@pytest.mark.asyncio
async def test_conversation_flow(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-flow"}}

    # 1. Hello
    await agent.ainvoke({"messages": [HumanMessage(content="Hello")]}, config=config)

    # 2. Regular message
    result = await agent.ainvoke({"messages": [HumanMessage(content="How are you?")]}, config=config)
    assert result["messages"][-1].content == "LLM Response"
