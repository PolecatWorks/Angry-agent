import pytest
import uuid
from langchain_core.tools import ToolException
from src.agent.tools.mfe import edit_visualization, browse_visualizations, read_visualization, add_visualization
from src.agent.structs import MFEContent, AgentState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

@pytest.mark.asyncio
async def test_browse_visualizations_happy_path():
    # Arrange
    mfe_id1 = uuid.uuid4().hex
    mfe_id2 = uuid.uuid4().hex
    mfe1 = MFEContent(
        id=mfe_id1,
        name="MFE 1",
        title="Title 1",
        description="Description 1",
        provider="mfe1",
        component="./Component1",
        content={"key": "value1"}
    )
    mfe2 = MFEContent(
        id=mfe_id2,
        name="MFE 2",
        title="Title 2",
        description="Description 2",
        provider="mfe1",
        component="./Component2",
        content={"key": "value2"}
    )
    mock_state = AgentState(visualizations=[mfe1, mfe2])

    # Act
    # Calling tool's coroutine directly passing state
    result = await browse_visualizations.coroutine(state=mock_state)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == mfe1
    assert result[1] == mfe2


@pytest.mark.asyncio
async def test_browse_visualizations_empty_state():
    # Arrange
    mock_state = AgentState(visualizations=[])

    # Act
    result = await browse_visualizations.coroutine(state=mock_state)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_read_visualization_happy_path():
    # Arrange
    mfe_id1 = uuid.uuid4().hex
    mfe1 = MFEContent(
        id=mfe_id1,
        name="MFE 1",
        title="Title 1",
        description="Description 1",
        provider="mfe1",
        component="./Component1",
        content={"key": "value1"}
    )
    mock_state = AgentState(visualizations=[mfe1])

    # Act
    result = await read_visualization.coroutine(id=mfe_id1, state=mock_state)

    # Assert
    assert result == mfe1


@pytest.mark.asyncio
async def test_read_visualization_missing_id():
    # Arrange
    mock_state = AgentState(visualizations=[])
    missing_id = uuid.uuid4().hex

    # Act & Assert
    with pytest.raises(ToolException) as exc_info:
        await read_visualization.coroutine(id=missing_id, state=mock_state)

    assert f"Visualization {missing_id} not found." in str(exc_info.value)


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
async def test_add_visualization_happy_path():
    # Arrange
    mfe_id = uuid.uuid4().hex
    new_mfe = MFEContent(
        id=mfe_id,
        name="New MFE",
        title="New Title",
        description="New description",
        provider="mfe1",
        component="./NewComponent",
        content={"key": "new"}
    )

    tool_call_id = "test_tool_call_add_123"

    # Act
    result = await add_visualization.coroutine(mfe=new_mfe, tool_call_id=tool_call_id)

    # Assert
    assert isinstance(result, Command)

    assert "visualizations" in result.update
    vis_updates = result.update["visualizations"]
    assert len(vis_updates) == 1
    add_data = vis_updates[0]

    assert add_data["action"] == "add"
    assert add_data["id"] == mfe_id
    assert add_data["name"] == "New MFE"
    assert add_data["content"] == {"key": "new"}

    assert "messages" in result.update
    messages = result.update["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], ToolMessage)
    assert messages[0].tool_call_id == tool_call_id
    assert f"Visualization {new_mfe.name} added successfully." in messages[0].content


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
