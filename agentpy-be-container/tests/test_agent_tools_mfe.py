import pytest
import uuid
from langchain_core.tools import ToolException
from src.agent.tools.mfe import (
    edit_visualization,
    browse_visualizations,
    read_visualization,
    add_visualization,
    inspect_active_mfe,
    patch_active_mfe,
    switch_active_mfe,
)
from src.agent.structs import (
    MFEContent,
    AgentState,
    JsonPatchOp,
    AiFieldAttribution,
    CanvasSelection,
    visualizations_reducer,
    apply_json_patches,
)
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
    result = await browse_visualizations.coroutine(state=mock_state)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == mfe1
    assert result[1] == mfe2


@pytest.mark.asyncio
async def test_browse_visualizations_empty_state():
    mock_state = AgentState(visualizations=[])
    result = await browse_visualizations.coroutine(state=mock_state)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_read_visualization_happy_path():
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

    result = await read_visualization.coroutine(id=mfe_id1, state=mock_state)
    assert result == mfe1


@pytest.mark.asyncio
async def test_read_visualization_missing_id():
    mock_state = AgentState(visualizations=[])
    missing_id = uuid.uuid4().hex

    with pytest.raises(ToolException) as exc_info:
        await read_visualization.coroutine(id=missing_id, state=mock_state)

    assert f"Visualization {missing_id} not found." in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_visualization_happy_path():
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
    result = await edit_visualization.coroutine(mfe=updated_mfe, state=mock_state, tool_call_id=tool_call_id)

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
    result = await add_visualization.coroutine(mfe=new_mfe, tool_call_id=tool_call_id)

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

    with pytest.raises(ToolException) as exc_info:
        await edit_visualization.coroutine(mfe=mfe, state=mock_state, tool_call_id="123")

    assert f"Visualization {missing_id} not found." in str(exc_info.value)


# --- Shared Canvas RFC 6902 Patching & Generic Tools Tests ---

def test_apply_json_patches_and_reducer_patch_action():
    mfe_id = "viz-patch-1"
    initial_mfe = MFEContent(
        id=mfe_id,
        name="Personal Form",
        title="User Profile",
        description="Live form",
        provider="mfe1",
        component="./PersonalDataFormWrapper",
        content={
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "fields": [{"name": "total_cents", "unit": "cents"}]
        }
    )

    patch_cmd = {
        "action": "patch",
        "id": mfe_id,
        "patches": [
            {"op": "replace", "path": "/firstName", "value": "Grace"},
            {"op": "replace", "path": "/fields/0/unit", "value": "USD"},
            {"op": "add", "path": "/phoneNumber", "value": "+1-555-0100"},
            {"op": "remove", "path": "/lastName"}
        ],
        "attributions": [
            {"path": "/firstName", "source": "ai", "confidence": 0.98, "rationale": "Updated first name"}
        ]
    }

    updated_list = visualizations_reducer([initial_mfe], [patch_cmd])
    assert len(updated_list) == 1
    updated = updated_list[0]
    assert updated.content["firstName"] == "Grace"
    assert updated.content["email"] == "john@example.com"
    assert updated.content["phoneNumber"] == "+1-555-0100"
    assert updated.content["fields"][0]["unit"] == "USD"
    assert "lastName" not in updated.content
    assert len(updated.attributions) == 1
    assert updated.attributions[0].path == "/firstName"
    assert updated.attributions[0].source == "ai"


@pytest.mark.asyncio
async def test_inspect_active_mfe_happy_path_and_selection():
    mfe_id = "viz-inspect-1"
    mfe = MFEContent(
        id=mfe_id,
        name="Personal Form",
        title="User Profile",
        description="Live form",
        provider="mfe1",
        component="./PersonalDataFormWrapper",
        content={"firstName": "Ada"},
        json_schema={"type": "object", "title": "PersonalDataForm"}
    )
    selection = CanvasSelection(
        canvas_id=mfe_id,
        path="/firstName",
        label="First Name",
        context={"currentValue": "Ada"}
    )
    mock_state = AgentState(visualizations=[mfe], active_selection=selection)

    # Inspect specific ID
    res_single = await inspect_active_mfe.coroutine(state=mock_state, id=mfe_id)
    assert res_single["visualization"]["id"] == mfe_id
    assert res_single["visualization"]["json_schema"]["title"] == "PersonalDataForm"
    assert res_single["active_selection"]["path"] == "/firstName"

    # Inspect all
    res_all = await inspect_active_mfe.coroutine(state=mock_state)
    assert len(res_all["visualizations"]) == 1
    assert res_all["active_selection"]["label"] == "First Name"


@pytest.mark.asyncio
async def test_patch_active_mfe_happy_path_and_missing_id():
    mfe_id = "viz-patch-tool"
    mfe = MFEContent(
        id=mfe_id,
        name="Personal Form",
        title="User Profile",
        description="Live form",
        provider="mfe1",
        component="./PersonalDataFormWrapper",
        content={"firstName": "John", "email": "john@example.com"}
    )
    mock_state = AgentState(visualizations=[mfe])

    patches = [
        JsonPatchOp(op="replace", path="/email", value="john.doe@fleet.mil")
    ]
    attributions = [
        AiFieldAttribution(path="/email", source="ai", confidence=0.95, rationale="Updated domain")
    ]

    cmd = await patch_active_mfe.coroutine(
        id=mfe_id,
        patches=patches,
        attributions=attributions,
        state=mock_state,
        tool_call_id="call-patch-1"
    )

    assert isinstance(cmd, Command)
    vis_cmd = cmd.update["visualizations"][0]
    assert vis_cmd["action"] == "patch"
    assert vis_cmd["id"] == mfe_id
    assert vis_cmd["patches"] == [{"op": "replace", "path": "/email", "value": "john.doe@fleet.mil"}]
    assert vis_cmd["attributions"][0]["rationale"] == "Updated domain"

    # Missing ID raises ToolException
    with pytest.raises(ToolException):
        await patch_active_mfe.coroutine(
            id="non-existent",
            patches=patches,
            state=mock_state,
            tool_call_id="call-patch-2"
        )


@pytest.mark.asyncio
async def test_switch_active_mfe_add_and_replace():
    existing_id = "viz-slot-1"
    existing_mfe = MFEContent(
        id=existing_id,
        name="Old Form",
        title="Old Title",
        description="Old Desc",
        provider="mfe1",
        component="./PersonalDataFormWrapper",
        content={"firstName": "John"}
    )
    mock_state = AgentState(visualizations=[existing_mfe])

    # Replace existing slot
    replace_cmd = await switch_active_mfe.coroutine(
        provider="data-engine",
        component="./DataAssetFormWrapper",
        name="Orders Asset Form",
        title="Orders Dataset",
        description="Semantic metadata form",
        initial_content={"dataset": "s3://lake/orders.parquet"},
        replace_id=existing_id,
        state=mock_state,
        tool_call_id="call-switch-1"
    )
    assert isinstance(replace_cmd, Command)
    assert replace_cmd.update["visualizations"][0]["action"] == "update"
    assert replace_cmd.update["visualizations"][0]["id"] == existing_id
    assert replace_cmd.update["visualizations"][0]["provider"] == "data-engine"
    assert replace_cmd.update["visualizations"][0]["component"] == "./DataAssetFormWrapper"

    # Mount new slot when replace_id is omitted
    add_cmd = await switch_active_mfe.coroutine(
        provider="data-engine",
        component="./JoinHypothesisReviewWrapper",
        name="Join Review",
        title="Join Review",
        description="HITL Join Card",
        initial_content={"jaccard": 0.94},
        state=mock_state,
        tool_call_id="call-switch-2"
    )
    assert isinstance(add_cmd, Command)
    assert add_cmd.update["visualizations"][0]["action"] == "add"
    assert add_cmd.update["visualizations"][0]["component"] == "./JoinHypothesisReviewWrapper"
