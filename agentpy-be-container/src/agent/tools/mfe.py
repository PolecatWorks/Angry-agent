from langchain_core.tools import tool, ToolException, InjectedToolCallId
import json
import uuid
import logging
from typing import List, Annotated, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.agent.structs import MFEContent, AgentState, JsonPatchOp, AiFieldAttribution

logger = logging.getLogger(__name__)

# --- BREAD (Browse, Read, Edit, Add, Delete) & Shared Canvas Interfaces for Visualizations ---

@tool
async def browse_visualizations(state: Annotated[AgentState, InjectedState]) -> List[MFEContent]:
    """
    Browse all visualizations for the current thread.
    Use this to see what visualizations are currently available and the order they are displayed.
    """
    return state.visualizations


class ReadVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to retrieve")

@tool(args_schema=ReadVisualizationInput)
async def read_visualization(id: str, state: Annotated[AgentState, InjectedState]) -> MFEContent:
    """
    Read the full details of a specific visualization by its ID.
    Use this when you need the full content of a visualization you already know the ID for.
    """
    for v in state.visualizations:
        if v.id == id:
            return v
    raise ToolException(f"Visualization {id} not found.")


class EditVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to edit")
    order_index: int | None = Field(default=None, description="Optional new order index for the visualization")


@tool()
async def edit_visualization(
    mfe: MFEContent,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Edit the content or description of an existing visualization.
    Use this when the user asks to modify or update a visualization that already exists.
    """
    # Find the existing visualization to get its MFE and Component
    existing = None
    for v in state.visualizations:
        if v.id == mfe.id:
            existing = v
            break

    if not existing:
        raise ToolException(f"Visualization {mfe.id} not found.")

    # Prepare update data for state reducer
    update_data = mfe.model_dump()
    update_data["action"] = "update"

    logger.info(f"Tool edit_visualization called: Requested update for {mfe.id}")
    # Return Command to trigger the visualizations reducer directly
    return Command(
        update={
            "visualizations": [update_data],
            "messages": [ToolMessage(content=f"Visualization {mfe.name} updated successfully.", tool_call_id=tool_call_id)]
        }
    )


class AddVisualizationInput(BaseModel):
    mfe: MFEContent = Field(description="The MFEContent object to be added to the visualisation")

@tool()
async def add_visualization(
    mfe: MFEContent,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Add a new visualization.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """

    logger.warning(f"Tool add_visualization called: Requested add for {mfe}")
    
    # Prepare update data for state reducer
    viz_data = mfe.model_dump()
    viz_data["action"] = "add"

    return Command(
        update={
            "visualizations": [viz_data],
            "messages": [ToolMessage(content=f"Visualization {mfe.name} added successfully.", tool_call_id=tool_call_id)]
        }
    )


class DeleteVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to delete")

@tool(args_schema=DeleteVisualizationInput)
async def delete_visualization(
    id: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Delete an existing visualization.
    Use this when the user asks to remove a visualization.
    """
    found = False
    for v in state.visualizations:
        if v.id == id:
            found = True
            break

    if not found:
        raise ToolException(f"Visualization {id} not found.")

    # Signal the deletion to the state reducer
    delete_data = {
        "id": id,
        "action": "delete"
    }

    logger.info(f"Tool delete_visualization called: Requested deletion for {id}")
    return Command(
        update={
            "visualizations": [delete_data],
            "messages": [ToolMessage(content=f"Visualization {id} deleted successfully.", tool_call_id=tool_call_id)]
        }
    )


# --- Generic Self-Describing Shared Canvas Tools ---

class InspectActiveMfeInput(BaseModel):
    id: Optional[str] = Field(default=None, description="Optional visualization ID to inspect. If omitted, returns all active visualizations and the user's currently focused element.")

@tool(args_schema=InspectActiveMfeInput)
async def inspect_active_mfe(
    state: Annotated[AgentState, InjectedState],
    id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inspect the live unsubmitted state, self-describing Draft-07 JSON Schema, AI attributions,
    and the user's currently focused element ('active_selection') on the RHS shared canvas.
    Always call this before patching a form if you need its schema or field paths.
    """
    active_sel = state.active_selection.model_dump() if state.active_selection else None

    if id:
        for v in state.visualizations:
            if v.id == id:
                return {
                    "visualization": v.model_dump(),
                    "active_selection": active_sel
                }
        raise ToolException(f"Visualization {id} not found.")

    return {
        "visualizations": [v.model_dump() for v in state.visualizations],
        "active_selection": active_sel
    }


@tool()
async def patch_active_mfe(
    id: str,
    patches: List[JsonPatchOp],
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    attributions: Optional[List[AiFieldAttribution]] = None,
) -> Command:
    """
    Apply fine-grained RFC 6902 JSON Patch operations ('add', 'replace', 'remove') in-place
    to a live MFE form or visualization on the RHS shared canvas without overwriting untouched fields
    or interrupting the user's active keyboard focus.
    """
    existing = None
    for v in state.visualizations:
        if v.id == id:
            existing = v
            break

    if not existing:
        raise ToolException(f"Visualization {id} not found.")

    serialized_patches = [p.model_dump() if hasattr(p, "model_dump") else p for p in patches]
    if attributions is None:
        serialized_attributions = [
            {"path": p["path"], "source": "ai", "rationale": "Updated by AI via patch_active_mfe"}
            for p in serialized_patches
            if isinstance(p, dict) and p.get("op") in ("add", "replace") and "path" in p
        ]
    else:
        serialized_attributions = [a.model_dump() if hasattr(a, "model_dump") else a for a in attributions]

    patch_command = {
        "action": "patch",
        "id": id,
        "patches": serialized_patches,
        "attributions": serialized_attributions
    }

    logger.info(f"Tool patch_active_mfe called: Applying {len(serialized_patches)} patches to {id}")
    return Command(
        update={
            "visualizations": [patch_command],
            "messages": [
                ToolMessage(
                    content=f"Applied {len(serialized_patches)} patch(es) to visualization {existing.name} ({id}).",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )


@tool()
async def switch_active_mfe(
    provider: str,
    component: str,
    name: str,
    title: str,
    description: str,
    initial_content: Dict[str, Any],
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_id: Optional[str] = None,
) -> Command:
    """
    Dynamically mount or switch the RHS shared canvas to any federated Micro-Frontend component
    (e.g. provider='mfe1', component='./PersonalDataFormWrapper' or provider='data-engine', component='./DataAssetFormWrapper').
    If replace_id is provided and exists, replaces that visualization slot in-place; otherwise adds a new visualization.
    """
    if replace_id:
        for v in state.visualizations:
            if v.id == replace_id:
                updated_mfe = MFEContent(
                    id=replace_id,
                    name=name,
                    title=title,
                    description=description,
                    provider=provider,
                    component=component,
                    content=initial_content
                )
                update_data = updated_mfe.model_dump()
                update_data["action"] = "update"
                return Command(
                    update={
                        "visualizations": [update_data],
                        "messages": [
                            ToolMessage(
                                content=f"Switched visualization {replace_id} to {provider}/{component}.",
                                tool_call_id=tool_call_id
                            )
                        ]
                    }
                )

    new_mfe = MFEContent(
        name=name,
        title=title,
        description=description,
        provider=provider,
        component=component,
        content=initial_content
    )
    add_data = new_mfe.model_dump()
    add_data["action"] = "add"
    return Command(
        update={
            "visualizations": [add_data],
            "messages": [
                ToolMessage(
                    content=f"Mounted {provider}/{component} ({new_mfe.id}) on shared canvas.",
                    tool_call_id=tool_call_id
                )
            ]
        }
    )
