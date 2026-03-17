"""
Tests for the agent conversation flow
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent
@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=BaseChatModel)
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="LLM Response"))
    return llm


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
async def test_image_intent(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-image"}}

    # Test Image Route
    input_msg = HumanMessage(content="Please draw a picture")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]

    assert "Here is your image:" in messages[-1].content
    assert messages[-1].additional_kwargs.get("image_url") == "https://picsum.photos/400/300"

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

@pytest.mark.asyncio
async def test_mfe_tool_call(mock_llm):
    tool_call = {
        "name": "get_mfe_content",
        "args": {},
        "id": "call_123",
        "type": "tool_call"
    }
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="", tool_calls=[tool_call]),
        AIMessage(content="Here is the MFE content you requested.")
    ]
    
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-mfe"}}

    input_msg = HumanMessage(content="Show me some JSON")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    
    # Final message content should be preserved (not suppressed)
    assert messages[-1].content == "Here is the MFE content you requested."
    assert "mfe_contents" in messages[-1].additional_kwargs
    mfe = messages[-1].additional_kwargs["mfe_contents"][0]
    assert mfe["mfe"] == "mfe1"
    assert mfe["component"] == "./JsonShowWrapper"
    assert "content" in mfe

@pytest.mark.asyncio
async def test_data_viz_tool_call(mock_llm):
    tool_call = {
        "name": "generate_data_visualization",
        "args": {
            "title": "Sales Performance",
            "datasets": [{"label": "Direct", "values": [{"x": 1, "y": 100}]}],
            "x_axis_type": "linear"
        },
        "id": "call_456",
        "type": "tool_call"
    }
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="", tool_calls=[tool_call]),
        AIMessage(content="Here is the chart.")
    ]
    
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-data-viz"}}

    input_msg = HumanMessage(content="Show me a chart of sales")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    
    # Final message content should be preserved (not suppressed)
    assert messages[-1].content == "Here is the chart."
    assert "mfe_contents" in messages[-1].additional_kwargs
    mfe = messages[-1].additional_kwargs["mfe_contents"][0]
    assert mfe["mfe"] == "mfe1"
    assert mfe["component"] == "./DataShowWrapper"
    assert mfe["content"]["title"] == "Sales Performance"


@pytest.mark.asyncio
async def test_mfe_content_detected_from_json_string(mock_llm):
    """Verify MFEContent serialised as a JSON string in ToolMessage is detected."""
    import json
    mfe_json = json.dumps({"mfe": "mfe1", "component": "./JsonShowWrapper", "content": {"key": "val"}})
    tool_call = {
        "name": "get_mfe_content",
        "args": {},
        "id": "call_str_1",
        "type": "tool_call"
    }
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="", tool_calls=[tool_call]),
        AIMessage(content="Done.")
    ]

    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-mfe-str"}}

    result = await agent.ainvoke({"messages": [HumanMessage(content="show json")]}, config=config)
    messages = result["messages"]

    assert messages[-1].content == "Done."
    assert "mfe_contents" in messages[-1].additional_kwargs
    mfe = messages[-1].additional_kwargs["mfe_contents"][0]
    assert mfe["mfe"] == "mfe1"
    assert mfe["component"] == "./JsonShowWrapper"


@pytest.mark.asyncio
async def test_non_mfe_tool_output_ignored(mock_llm):
    """Tool output that does not match MFEContent schema should not appear in mfe_contents."""
    # The get_mfe_content tool returns a valid MFE dict, but we override the
    # mock to make the LLM call a hypothetical tool returning non-MFE data.
    tool_call = {
        "name": "get_mfe_content",
        "args": {},
        "id": "call_non_mfe",
        "type": "tool_call"
    }
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="", tool_calls=[tool_call]),
        AIMessage(content="No MFE here.")
    ]

    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-no-mfe"}}

    result = await agent.ainvoke({"messages": [HumanMessage(content="show json")]}, config=config)
    messages = result["messages"]

    # get_mfe_content returns valid MFE, so it WILL be detected
    assert "mfe_contents" in messages[-1].additional_kwargs
    # Content preserved
    assert messages[-1].content == "No MFE here."
