import pytest
from langchain_core.tools import ToolException
from src.agent.tools.mfe import delete_visualization
from src.agent.structs import MFEContent, AgentState

@pytest.mark.asyncio
async def test_delete_visualization_happy_path():
    # Setup mock state with a visualization
    mfe_id = "test_id_123"
    mock_mfe = MFEContent(
        id=mfe_id,
        name="test_viz",
        title="Test Viz",
        description="A test visualization",
        provider="test_provider",
        component="TestComponent",
        content={"data": "test"}
    )
    mock_state = AgentState(visualizations=[mock_mfe])
    tool_call_id = "tool_call_456"

    # Call the tool
    command = await delete_visualization.ainvoke({"id": mfe_id, "state": mock_state, "tool_call_id": tool_call_id})

    # Verify the returned Command
    assert command is not None
    assert "visualizations" in command.update
    assert len(command.update["visualizations"]) == 1

    update_data = command.update["visualizations"][0]
    assert update_data["action"] == "delete"
    assert update_data["id"] == mfe_id

    assert "messages" in command.update
    assert len(command.update["messages"]) == 1
    tool_message = command.update["messages"][0]
    assert tool_message.tool_call_id == tool_call_id
    assert f"Visualization {mfe_id} deleted successfully." in tool_message.content

@pytest.mark.asyncio
async def test_delete_visualization_missing_id():
    # Setup mock state with a visualization
    mock_mfe = MFEContent(
        id="existing_id",
        name="test_viz",
        title="Test Viz",
        description="A test visualization",
        provider="test_provider",
        component="TestComponent",
        content={"data": "test"}
    )
    mock_state = AgentState(visualizations=[mock_mfe])
    tool_call_id = "tool_call_456"
    missing_id = "non_existent_id"

    # Call the tool with a missing ID and verify it raises a ToolException
    with pytest.raises(ToolException, match=f"Visualization {missing_id} not found."):
        await delete_visualization.ainvoke({"id": missing_id, "state": mock_state, "tool_call_id": tool_call_id})
