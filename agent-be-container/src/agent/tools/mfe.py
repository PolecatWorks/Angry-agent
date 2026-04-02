from langchain_core.tools import ToolException
import json
import uuid
import logging
from typing import List, Annotated
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState

from src.agent.structs import MFEContent, AgentState

logger = logging.getLogger(__name__)

# --- BREAD (Browse, Read, Edit, Add, Delete) Interfaces for Visualizations ---

@tool
async def browse_visualizations(state: Annotated[AgentState, InjectedState]) -> List[MFEContent]:
    """
    Browse all visualizations pinned to the right pane for the current thread.
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
    content: dict = Field(description="The new content for the MFE")
    name: str | None = Field(default=None, description="Optional new display name for the visualization")
    description: str | None = Field(default=None, description="Optional new description")

@tool(args_schema=EditVisualizationInput)
async def edit_visualization(id: str, content: dict, name: str | None, description: str | None, state: Annotated[AgentState, InjectedState]) -> str:
    """
    Edit the content or description of an existing visualization.
    Use this when the user asks to modify or update a visualization that is already on the right pane.
    """
    # Find the existing visualization to get its MFE and Component
    existing = None
    for v in state.visualizations:
        if v.id == id:
            existing = v
            break
    
    if not existing:
        return f"Error: Visualization {id} not found."

    # Signal the change to the packager node
    update_data = {
        "id": id,
        "mfe": existing.mfe,
        "component": existing.component,
        "content": content,
        "name": name or existing.name,
        "description": description or existing.description,
        "pin_to_pane": True,
        "action": "update"
    }

    logger.info(f"Tool edit_visualization called: Requested update for {id}")
    return json.dumps(update_data)


class AddVisualizationInput(BaseModel):
    mfe: str = Field(description="The source MFE where the component is defined (e.g. 'mfe1')")
    component: str = Field(description="The name of the MFE component to render")
    content: dict = Field(description="The content to render in the MFE")
    name: str = Field(description="The display name or label for the visualization")
    description: str = Field(description="A description of the visualization to help keep context")

@tool(args_schema=AddVisualizationInput)
async def add_visualization(mfe: str, component: str, content: dict, name: str, description: str) -> str:
    """
    Add a new visualization for the current thread and pin it to the right pane.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """
    viz_id = str(uuid.uuid4())
    
    # Signal the new visualization to the packager node
    add_data = {
        "id": viz_id,
        "mfe": mfe,
        "component": component,
        "content": content,
        "name": name,
        "description": description,
        "pin_to_pane": True,
        "action": "add"
    }

    logger.info(f"Tool add_visualization called: Requested add for {viz_id}")
    return json.dumps(add_data)


class DeleteVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to delete")

@tool(args_schema=DeleteVisualizationInput)
async def delete_visualization(id: str, state: Annotated[AgentState, InjectedState]) -> str:
    """
    Delete an existing visualization from the right pane.
    Use this when the user asks to remove a visualization.
    """
    found = False
    for v in state.visualizations:
        if v.id == id:
            found = True
            break
    
    if not found:
        return f"Error: Visualization {id} not found."

    # Signal the deletion to the packager node
    delete_data = {
        "id": id,
        "action": "delete"
    }

    logger.info(f"Tool delete_visualization called: Requested deletion for {id}")
    return json.dumps(delete_data)
