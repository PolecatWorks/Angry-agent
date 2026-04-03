import pytest
import uuid
from langchain_core.tools import ToolException
from src.agent.tools.mfe import edit_visualization
from src.agent.structs import MFEContent, AgentState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

@pytest.mark.asyncio
async def test_edit_visualization_happy_path():
    # Arrange
    mfe_id = uuid.uuid4().hex
    original_mfe = MFEContent(
        id=mfe_id,
        name="Original MFE",
        title="Original Title",
        description="Original description",
        provider="mfe1",
        component="./OriginalComponent",
        content={"key": "old"}
    )
    mock_state = AgentState(visualizations=[original_mfe])

    updated_mfe = MFEContent(
        id=mfe_id,
        name="Updated MFE",
        title="Updated Title",
        description="Updated description",
        provider="mfe1",
        component="./OriginalComponent",
        content={"key": "new"}
    )

    tool_call_id = "test_tool_call_123"

    # Act
    # edit_visualization is a tool, so we access its coroutine method for direct state/tool_call_id injection
    result = await edit_visualization.coroutine(mfe=updated_mfe, state=mock_state, tool_call_id=tool_call_id)

    # Assert
    assert isinstance(result, Command)

    assert "visualizations" in result.update
    vis_updates = result.update["visualizations"]
    assert len(vis_updates) == 1
    update_data = vis_updates[0]

    assert update_data["action"] == "update"
    assert update_data["id"] == mfe_id
    assert update_data["name"] == "Updated MFE"
    assert update_data["content"] == {"key": "new"}

    assert "messages" in result.update
    messages = result.update["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], ToolMessage)
    assert messages[0].tool_call_id == tool_call_id
    assert "Visualization Updated MFE updated successfully." in messages[0].content


@pytest.mark.asyncio
async def test_edit_visualization_missing_id():
    # Arrange
    mock_state = AgentState(visualizations=[])

    missing_id = uuid.uuid4().hex
    mfe = MFEContent(
        id=missing_id,
        name="Missing MFE",
        title="Missing Title",
        description="Missing description",
        provider="mfe1",
        component="./MissingComponent",
        content={"key": "value"}
    )

    # Act & Assert
    with pytest.raises(ToolException) as exc_info:
        await edit_visualization.coroutine(mfe=mfe, state=mock_state, tool_call_id="123")

    assert f"Visualization {missing_id} not found." in str(exc_info.value)
