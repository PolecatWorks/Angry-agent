import pytest
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from unittest.mock import MagicMock, AsyncMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent, extract_mermaid

def test_extract_mermaid():
    text = """
Here is a diagram:
```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```
And another one:
```mermaid
pie title Pets
    "Dogs" : 386
    "Cats" : 85
```
    """
    diagrams = extract_mermaid(text)
    assert len(diagrams) == 2
    assert "graph TD;" in diagrams[0]
    assert "pie title Pets" in diagrams[1]

@pytest.mark.asyncio
async def test_mermaid_post_processing():
    # Setup LLM to return mermaid content
    mermaid_content = "```mermaid\ngraph TD; A-->B\n```"
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=mermaid_content))
    
    checkpointer = MemorySaver()
    agent = create_agent(llm=mock_llm, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "mermaid-test"}}
    
    # Invoke agent
    result = await agent.ainvoke({"messages": [HumanMessage(content="Explain the process")]}, config=config)
    
    # Check if mermaid was extracted into metadata
    last_msg = result["messages"][-1]
    assert last_msg.content == mermaid_content
    assert "mermaid_diagrams" in last_msg.additional_kwargs
    assert len(last_msg.additional_kwargs["mermaid_diagrams"]) == 1
    assert "graph TD; A-->B" in last_msg.additional_kwargs["mermaid_diagrams"][0]
