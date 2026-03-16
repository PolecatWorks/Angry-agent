import pytest
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent
from agent.tools import get_tools

def test_visualize_graph_tool_registration():
    # Test that when a builder is passed, the tool is included
    from langgraph.graph import StateGraph
    from agent import AgentState
    builder = StateGraph(AgentState)
    tools = get_tools(builder)
    
    tool_names = [t.name for t in tools]
    assert "visualize_graph" in tool_names

@pytest.mark.asyncio
async def test_visualize_graph_tool_execution():
    # We need a real-ish setup to actually call the tool through the agent
    # or we can just call the tool's function directly.
    from langgraph.graph import StateGraph
    from agent import AgentState
    
    builder = StateGraph(AgentState)
    tools = get_tools(builder)
    
    # Find the visualize_graph tool
    vg_tool = next(t for t in tools if t.name == "visualize_graph")
    
    # Adding some dummy nodes/edges to make the graph non-empty
    builder.add_node("start", lambda x: x)
    builder.set_entry_point("start")
    builder.add_edge("start", END)
    
    # Call the tool
    # Mermaid draw usually requires at least some edges
    result = vg_tool.invoke({})
    
    assert result.mfe == "mfe1"
    assert result.component == "./MermaidShowWrapper"
    assert "graph TD" in result.content["content"] or "flowchart TD" in result.content["content"]

@pytest.mark.asyncio
async def test_agent_uses_visualize_graph_tool():
    # Setup LLM to call the visualize_graph tool
    from unittest.mock import MagicMock, AsyncMock
    from langchain_core.language_models import BaseChatModel
    
    llm = MagicMock(spec=BaseChatModel)
    llm.bind_tools.return_value = llm
    
    # First call returns tool call, second call returns content
    llm.ainvoke = AsyncMock(side_effect=[
        AIMessage(content="", tool_calls=[{
            "name": "visualize_graph",
            "args": {},
            "id": "call_1",
            "type": "tool_call"
        }]),
        AIMessage(content="Here is my graph diagram.")
    ])
    
    checkpointer = MemorySaver()
    agent = create_agent(llm=llm, checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "vg-test"}}
    
    result = await agent.ainvoke({"messages": [HumanMessage(content="Show me your graph")]}, config=config)
    
    # Check that visualize_graph was called (implicitly by checking result)
    # The post_process node should have extracted the MFE content
    last_msg = result["messages"][-1]
    assert "mfe_contents" in last_msg.additional_kwargs
    assert len(last_msg.additional_kwargs["mfe_contents"]) > 0
    mfe = last_msg.additional_kwargs["mfe_contents"][0]
    assert mfe["mfe"] == "mfe1"
    assert mfe["component"] == "./MermaidShowWrapper"
    assert "graph TD" in mfe["content"]["content"] or "flowchart TD" in mfe["content"]["content"]
