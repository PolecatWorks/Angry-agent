"""
Tests for the agent conversation flow
"""
import pytest
from unittest.mock import MagicMock
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent

@pytest.mark.asyncio
async def test_hello_intent():
    checkpointer = MemorySaver()
    agent = create_agent(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-hello"}}

    # Test Hello
    input_msg = HumanMessage(content="Hello world")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "Hello there!"

@pytest.mark.asyncio
async def test_echo_intent():
    checkpointer = MemorySaver()
    agent = create_agent(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-echo"}}

    # Test Echo
    input_msg = HumanMessage(content="Testing 123")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "Echo: Testing 123"

@pytest.mark.asyncio
async def test_conversation_flow():
    checkpointer = MemorySaver()
    agent = create_agent(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-flow"}}

    # 1. Hello
    await agent.ainvoke({"messages": [HumanMessage(content="Hello")]}, config=config)

    # 2. Regular message
    result = await agent.ainvoke({"messages": [HumanMessage(content="How are you?")]}, config=config)
    assert result["messages"][-1].content == "Echo: How are you?"
