from langchain_core.tools import ToolException
import json
import uuid
import re
import logging
import sys
import os
from typing import Any, List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from src.config import DbOptionsConfig
from src.agent.structs import MFEContent
from src.database import get_db_pool

logger = logging.getLogger(__name__)

async def save_visualization_to_db(thread_id: str, mfe: str, component: str, content: dict, name: str, description: str, pin_to_pane: bool = True) -> str:
    viz_id = str(uuid.uuid4())
    content_json = json.dumps(content)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get the max order_index to append
        row = await conn.fetchrow("SELECT MAX(order_index) as max_idx FROM visualizations WHERE thread_id = $1", thread_id)
        next_idx = (row["max_idx"] + 1) if row and row["max_idx"] is not None else 0

        await conn.execute(
            """
            INSERT INTO visualizations (id, thread_id, mfe, component, content, name, description, order_index, pin_to_pane)
            VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
            """,
            viz_id, thread_id, mfe, component, content_json, name, description, next_idx, pin_to_pane
        )
    return viz_id



# --- BREAD (Browse, Read, Edit, Add, Delete) Interfaces for Visualizations ---

@tool
async def browse_visualizations(config: RunnableConfig) -> List[MFEContent]:
    """
    Browse all visualizations pinned to the right pane for the current thread.
    Use this to see what visualizations are currently available and the order they are displayed.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        raise ToolException("No thread_id found in context.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, mfe, component, content, name, description, order_index, pin_to_pane FROM visualizations WHERE thread_id = $1 ORDER BY order_index ASC",
            thread_id
        )
        v_list = []
        for r in rows:
            v = dict(r)
            if isinstance(v.get("content"), str):
                v["content"] = json.loads(v["content"])
            v_list.append(MFEContent.model_validate(v))
        return v_list


class ReadVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to retrieve")

@tool(args_schema=ReadVisualizationInput)
async def read_visualization(id: str, config: RunnableConfig) -> MFEContent:
    """
    Read the full details of a specific visualization by its ID.
    Use this when you need the full content of a visualization you already know the ID for.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        raise ToolException("No thread_id found in context.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, mfe, component, content, name, description, order_index, pin_to_pane FROM visualizations WHERE id = $1::uuid AND thread_id = $2",
            id, thread_id
        )

        if not row:
            raise ToolException(f"Visualization {id} not found.")
        v = dict(row)
        if isinstance(v.get("content"), str):
            v["content"] = json.loads(v["content"])
        return MFEContent.model_validate(v)


class EditVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to edit")
    content: dict = Field(description="The new content for the MFE")
    name: str | None = Field(default=None, description="Optional new display name for the visualization")
    description: str | None = Field(default=None, description="Optional new description")

@tool(args_schema=EditVisualizationInput)
async def edit_visualization(id: str, content: dict, name: str | None, description: str | None, config: RunnableConfig) -> str:
    """
    Edit the content or description of an existing visualization.
    Use this when the user asks to modify or update a visualization that is already on the right pane.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    content_json = json.dumps(content)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if description is not None and name is not None:
            result = await conn.execute(
                """
                UPDATE visualizations
                SET content = $1::jsonb, name = $2, description = $3, updated_at = NOW()
                WHERE id = $4::uuid AND thread_id = $5
                """,
                content_json, name, description, id, thread_id
            )
        elif description is not None:
            result = await conn.execute(
                """
                UPDATE visualizations
                SET content = $1::jsonb, description = $2, updated_at = NOW()
                WHERE id = $3::uuid AND thread_id = $4
                """,
                content_json, description, id, thread_id
            )
        elif name is not None:
            result = await conn.execute(
                """
                UPDATE visualizations
                SET content = $1::jsonb, name = $2, updated_at = NOW()
                WHERE id = $3::uuid AND thread_id = $4
                """,
                content_json, name, id, thread_id
            )
        else:
            result = await conn.execute(
                """
                UPDATE visualizations
                SET content = $1::jsonb, updated_at = NOW()
                WHERE id = $2::uuid AND thread_id = $3
                """,
                content_json, id, thread_id
            )

        if result == "UPDATE 0":
            return f"Error: Visualization {id} not found or does not belong to this thread."

    logger.info(f"Tool edit_visualization called: Edited {id}")
    return f"Successfully edited visualization {id}"


class AddVisualizationInput(BaseModel):
    mfe: str = Field(description="The source MFE where the component is defined (e.g. 'mfe1')")
    component: str = Field(description="The name of the MFE component to render")
    content: dict = Field(description="The content to render in the MFE")
    name: str = Field(description="The display name or label for the visualization")
    description: str = Field(description="A description of the visualization to help keep context")

@tool(args_schema=AddVisualizationInput)
async def add_visualization(mfe: str, component: str, content: dict, name: str, description: str, config: RunnableConfig) -> str:
    """
    Add a new visualization for the current thread and pin it to the right pane.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    viz_id = await save_visualization_to_db(thread_id, mfe, component, content, name, description)

    logger.info(f"Tool add_visualization called: Added {viz_id} for thread {thread_id}")
    return f"Successfully added visualization with ID: {viz_id}"


class DeleteVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to delete")

@tool(args_schema=DeleteVisualizationInput)
async def delete_visualization(id: str, config: RunnableConfig) -> str:
    """
    Delete an existing visualization from the right pane.
    Use this when the user asks to remove a visualization.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM visualizations WHERE id = $1::uuid AND thread_id = $2",
            id, thread_id
        )

        if result == "DELETE 0":
            return f"Error: Visualization {id} not found or does not belong to this thread."

    logger.info(f"Tool delete_visualization called: Deleted {id}")
    return f"Successfully deleted visualization {id}"
