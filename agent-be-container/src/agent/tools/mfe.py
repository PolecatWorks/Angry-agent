from langchain_core.tools import tool, ToolException, InjectedToolCallId
import json
import uuid
import logging
from typing import List, Annotated, Any
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.agent.structs import MFEContent, AgentState, _try_parse_mfe_content

logger = logging.getLogger(__name__)

# --- BREAD (Browse, Read, Edit, Add, Delete) Interfaces for Visualizations ---

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
    mfe: Any = Field(description="The MFEContent object or data to be edited")
    order_index: int | None = Field(default=None, description="Optional new order index for the visualization")


@tool(args_schema=EditVisualizationInput)
async def edit_visualization(
    mfe: Any,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    order_index: int | None = None,
) -> Command:
    """
    Edit the content or description of an existing visualization.
    Use this when the user asks to modify or update a visualization that already exists.
    """
    mfe_obj = _try_parse_mfe_content(mfe)
    if not mfe_obj:
        raise ToolException(f"Invalid MFEContent provided: {mfe}")

    # Find the existing visualization to get its MFE and Component
    existing = None
    for v in state.visualizations:
        if v.id == mfe_obj.id:
            existing = v
            break

    if not existing:
        raise ToolException(f"Visualization {mfe_obj.id} not found.")

    # Prepare update data for state reducer
    update_data = mfe_obj.model_dump()
    update_data["action"] = "update"
    if order_index is not None:
        update_data["order_index"] = order_index

    logger.info(f"Tool edit_visualization called: Requested update for {mfe_obj.id}")
    # Return Command to trigger the visualizations reducer directly
    return Command(
        update={
            "visualizations": [update_data],
            "messages": [ToolMessage(content=f"Visualization {mfe_obj.name} updated successfully.", tool_call_id=tool_call_id)]
        }
    )


class AddVisualizationInput(BaseModel):
    mfe: Any = Field(description="The MFEContent object or data to be added to the visualisation. Should include name, title, description, provider, component, and content.")

@tool(args_schema=AddVisualizationInput)
async def add_visualization(
    mfe: Any,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Add a new visualization.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """
    mfe_obj = _try_parse_mfe_content(mfe)
    if not mfe_obj:
         # Log the raw input for debugging
        logger.error(f"Failed to parse mfe content in add_visualization. Raw: {mfe}")
        raise ToolException(f"Invalid MFEContent provided. Expected an object with name, title, description, provider, component, and content. Received type {type(mfe)}: {mfe}")


    logger.info(f"Tool add_visualization called: Requested add for {mfe_obj.id}")
    
    # Prepare update data for state reducer
    viz_data = mfe_obj.model_dump()
    viz_data["action"] = "add"

    return Command(
        update={
            "visualizations": [viz_data],
            "messages": [ToolMessage(content=f"Visualization {mfe_obj.name} added successfully.", tool_call_id=tool_call_id)]
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
