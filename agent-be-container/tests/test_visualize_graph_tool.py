import pytest
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END

# Add src to path
# Add container root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agent import create_agent
from src.agent.tools import get_tools

def test_visualize_graph_tool_registration():
    # Test that when a builder is passed, the tool is included
    from langgraph.graph import StateGraph
    from agent import AgentState
    builder = StateGraph(AgentState)
    tools = get_tools(builder)

    tool_names = [t.name for t in tools]
    assert "visualize_graph" in tool_names
