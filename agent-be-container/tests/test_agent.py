"""
Tests for the agent conversation flow
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver

# Add src to path
# Add container root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agent import create_agent
@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=BaseChatModel)
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="LLM Response"))
    # Mock with_structured_output for the packager_node
    # It should return a mock that when ainvoked returns an MFEContainer
    structured_mock = MagicMock()
    from src.agent.structs import MFEContainer, MFEContent

    async def smart_packager_invoke(messages):
        mfes = []
        from langchain_core.messages import SystemMessage
        for m in messages:
            if isinstance(m, SystemMessage):
                continue

            # Check AIMessage tool_calls
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    name = tc.get("name")
                    if name == "generate_data_visualization":
                        mfes.append(MFEContent(provider="mfe1", component="./DataShowWrapper", content={"title": "Sales Performance"}, title="Data Viz", pin_to_pane=False, name="Data Viz", description="Data Viz"))
                    elif name in ["get_mfe_content", "generate_mfe_of_json"]:
                         mfes.append(MFEContent(provider="mfe1", component="./JsonShowWrapper", content={"key": "val"}, title="JSON", pin_to_pane=False, name="JSON", description="JSON"))
                    elif name == "generate_mfe_of_markdown":
                         mfes.append(MFEContent(provider="mfe1", component="./MarkdownShowWrapper", content={"markdown_content": "Content"}, title="Markdown", pin_to_pane=False, name="Markdown", description="Markdown"))

            # Check ToolMessage content or malformed AI content
            if hasattr(m, "content") and isinstance(m.content, str) and m.content:
                if '"component": "./DataShowWrapper"' in m.content or "generate_data_visualization" in m.content:
                    mfes.append(MFEContent(provider="mfe1", component="./DataShowWrapper", content={"title": "Sales Performance"}, title="Data Viz", name="Data Viz", description="Data Viz"))
                elif '"component": "./JsonShowWrapper"' in m.content or "get_mfe_content" in m.content or "generate_mfe_of_json" in m.content:
                    mfes.append(MFEContent(provider="mfe1", component="./JsonShowWrapper", content={"key": "val"}, title="JSON", name="JSON", description="JSON"))
                elif '"component": "./MarkdownShowWrapper"' in m.content or "generate_mfe_of_markdown" in m.content or "poem" in m.content.lower():
                    mfes.append(MFEContent(provider="mfe1", component="./MarkdownShowWrapper", content={"markdown_content": "Content"}, title="Markdown", name="Markdown", description="Markdown"))
                if "pin_this" in m.content.lower():
                    mfes.append(MFEContent(provider="mfe1", component="./PinnedWrapper", content={"key": "val"}, title="Pinned Visual", name="Pinned Visual", description="Pinned description"))

        # Deduplicate
        seen_components = set()
        unique_mfes = []
        for mfe in mfes:
            if mfe.component not in seen_components:
                unique_mfes.append(mfe)
                seen_components.add(mfe.component)
        return MFEContainer(mfes=unique_mfes)

    structured_mock.ainvoke = AsyncMock(side_effect=smart_packager_invoke)
    llm.with_structured_output.return_value = structured_mock
    return llm


@pytest.mark.asyncio
async def test_hello_intent(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-hello"}}

    # Test Hello
    input_msg = HumanMessage(content="Hello world")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "Hello there!"

@pytest.mark.asyncio
async def test_image_intent(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
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
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-llm"}}

    # Test LLM Route
    input_msg = HumanMessage(content="Testing 123")
    result = await agent.ainvoke({"messages": [input_msg]}, config=config)
    messages = result["messages"]
    assert messages[-1].content == "LLM Response"

@pytest.mark.asyncio
async def test_conversation_flow(mock_llm):
    checkpointer = MemorySaver()
    agent = create_agent(main_llm=mock_llm, packager_llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-flow"}}

    # 1. Hello
    await agent.ainvoke({"messages": [HumanMessage(content="Hello")]}, config=config)

    # 2. Regular message
    result = await agent.ainvoke({"messages": [HumanMessage(content="How are you?")]}, config=config)
    assert result["messages"][-1].content == "LLM Response"
