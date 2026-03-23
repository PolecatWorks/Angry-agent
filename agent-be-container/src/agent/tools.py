from langchain_core.tools import tool
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from typing import Any, List, Literal
from .structs import MFEContent

# @tool
# def get_mfe_content(demo_type: str = "json"):
#     """
#     Returns a reference to a Micro-Frontend component and some content to be injected into it.
#     This tool is used to display interactive or structured content in the UI via an MFE.
#     Args:
#         demo_type: The type of demonstration to show (e.g., 'json', 'chart', 'stats').
#     """
#     logger.info("Tool get_mfe_content called")
#     return {
#         "mfe": "mfe1",
#         "component": "./JsonShowWrapper",
#         "content": {
#             "name": "Initial Demonstration",
#             "description": "This is a basic JSON object returned by the MFE tool.",
#             "timestamp": "2026-03-15T11:58:07Z",
#             "status": "success",
#             "data": [
#                 {"id": 1, "value": "A"},
#                 {"id": 2, "value": "B"},
#                 {"id": 3, "value": "C"}
#             ]
#         }
#     }


class JsonInput(BaseModel):
    json_content: Any = Field(description="The JSON object to render")
    title: str = Field(description="The title of the JSON object")

@tool(args_schema=JsonInput)
def generate_mfe_of_json(json_content: Any, title: str) -> MFEContent:
    """
    Generate a pretty rendered version of the input JSON.
    """
    logger.info(f"Tool generate_mfe_of_json called: {json_content}")
    return MFEContent(
        mfe="mfe1",
        component="./JsonShowWrapper",
        content={
            "content": json_content
        }
    )


class MarkdownInput(BaseModel):
    markdown_content: str = Field(description="The full markdown string to be rendered in the UI.")

@tool(args_schema=MarkdownInput)
def generate_mfe_of_markdown(markdown_content: str) -> MFEContent:
    """
    Render and display markdown text in the UI.
    Use this tool for ANY formatted text, headers, or lists.
    """
    # The LLM doesn't actually 'see' the execution logic below,
    # only the docstring and the MarkdownInput schema.

    logger.info(f"Tool generate_mfe_of_markdown called: {markdown_content}")
    return MFEContent(
        mfe="mfe1",
        component="./MarkdownShowWrapper",
        content={
            "content": markdown_content
        }
    )


class TextInput(BaseModel):
    text_content: str = Field(description="The full plain text string to be rendered in the UI.")

@tool(args_schema=TextInput)
def generate_mfe_of_text(text_content: str) -> MFEContent:
    """
    Render and display plain text in the UI.
    Use this tool for logs, raw output, or simple text that should not be interpreted as markdown.
    You can use it as preamble or description before and after more complex visualisation components.
    It only supports line wrapping and basic styling.
    """
    logger.info(f"Tool generate_mfe_of_text called: {text_content}")
    return MFEContent(
        mfe="mfe1",
        component="./TextShowWrapper",
        content={
            "content": text_content
        }
    )


class MermaidInput(BaseModel):
    mermaid_content: str = Field(description="The full mermaid string to be rendered in the UI. Do not include ```mermaid ... ``` markers in the content.")
    title: str = Field(description="The title of the mermaid diagram")

@tool(args_schema=MermaidInput)
def generate_mfe_of_mermaid(mermaid_content: str, title: str) -> MFEContent:
    """
    Generate a pretty rendered version of the input mermaid diagram.
    """
    logger.info(f"Tool generate_mfe_of_mermaid called: {mermaid_content}")
    return MFEContent(
        mfe="mfe1",
        component="./MermaidShowWrapper",
        content={
            "title": title,
            "content": mermaid_content
        }
    )


class DataPoint(BaseModel):
    x: Any = Field(description="The X value (number, string, or date string)")
    y: float = Field(description="The Y value (number)")

class Dataset(BaseModel):
    label: str = Field(description="Name of the dataset")
    values: List[DataPoint] = Field(description="List of data points")
    color: str | None = Field(default=None, description="Optional CSS color hex")

class DataVizInput(BaseModel):
    title: str = Field(description="The title of the visualization")
    datasets: List[Dataset] = Field(description="List of datasets to plot")
    x_axis_type: Literal["linear", "time", "band"] = Field(default="linear", description="Scale type for X axis")

@tool(args_schema=DataVizInput)
def generate_data_visualization(title: str, datasets: List[Dataset], x_axis_type: str = "linear") -> MFEContent:
    """
    Generates a high-quality data visualization (line graph) in the UI.
    Use this tool when the user asks for charts, graphs, trends, or data comparisons.
    """
    logger.info(f"Tool generate_data_visualization called: {title}")
    # Convert datasets back to dicts for the MFE
    datasets_dict = [d.model_dump() for d in datasets]
    return MFEContent(
        mfe="mfe1",
        component="./DataShowWrapper",
        content={
            "title": title,
            "content": datasets_dict,
            "xType": x_axis_type
        }
    )


import json
import uuid
from langchain_core.runnables import RunnableConfig
from ..database import get_db_pool

class CreateVisualizationInput(BaseModel):
    mfe: str = Field(description="The source MFE where the component is defined (e.g. 'mfe1')")
    component: str = Field(description="The name of the MFE component to render")
    content: dict = Field(description="The content to render in the MFE")
    description: str = Field(description="A description of the visualization to help keep context")

@tool(args_schema=CreateVisualizationInput)
async def create_visualization(mfe: str, component: str, content: dict, description: str, config: RunnableConfig) -> str:
    """
    Creates a new visualization for the current thread and pins it to the right pane.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    viz_id = str(uuid.uuid4())
    content_json = json.dumps(content)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get the max order_index to append
        row = await conn.fetchrow("SELECT MAX(order_index) as max_idx FROM visualizations WHERE thread_id = $1", thread_id)
        next_idx = (row["max_idx"] + 1) if row and row["max_idx"] is not None else 0

        await conn.execute(
            """
            INSERT INTO visualizations (id, thread_id, mfe, component, content, description, order_index)
            VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            viz_id, thread_id, mfe, component, content_json, description, next_idx
        )

    logger.info(f"Tool create_visualization called: Created {viz_id} for thread {thread_id}")
    return f"Successfully created visualization with ID: {viz_id}"


class UpdateVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to update")
    content: dict = Field(description="The new content for the MFE")
    description: str | None = Field(default=None, description="Optional new description")

@tool(args_schema=UpdateVisualizationInput)
async def update_visualization(id: str, content: dict, description: str | None, config: RunnableConfig) -> str:
    """
    Updates the content or description of an existing visualization.
    Use this when the user asks to modify or update a visualization that is already on the right pane.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    content_json = json.dumps(content)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if description is not None:
            result = await conn.execute(
                """
                UPDATE visualizations
                SET content = $1::jsonb, description = $2, updated_at = NOW()
                WHERE id = $3::uuid AND thread_id = $4
                """,
                content_json, description, id, thread_id
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

    logger.info(f"Tool update_visualization called: Updated {id}")
    return f"Successfully updated visualization {id}"


class DeleteVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to delete")

@tool(args_schema=DeleteVisualizationInput)
async def delete_visualization(id: str, config: RunnableConfig) -> str:
    """
    Deletes an existing visualization from the right pane.
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


def get_tools(builder):
    """Returns a list of tools available for the agent."""
    # tools = [generate_mfe_of_json, generate_data_visualization]
    tools = [
        generate_data_visualization,
        generate_mfe_of_markdown,
        generate_mfe_of_text,
        generate_mfe_of_json,
        generate_mfe_of_mermaid,
        create_visualization,
        update_visualization,
        delete_visualization
    ]

    @tool
    def visualize_graph() -> MFEContent:
        """
        Returns a mermaid diagram showing the internal structure and flow of this AI agent's LangGraph.
        Use this when the user asks 'how do you work?', 'show me your graph', or 'what is your architecture?'.
        """
        logger.info("Tool visualize_graph called")
        # StateGraph builder doesn't have get_graph() in all versions;
        # CompiledGraph does. If it's the builder, we compile it briefly to get the graph structure.
        if hasattr(builder, 'get_graph'):
            mermaid_code = builder.get_graph().draw_mermaid()
        else:
            mermaid_code = builder.compile().get_graph().draw_mermaid()

        return MFEContent(
            mfe="mfe1",
            component="./MermaidShowWrapper",
            content={
                "content": mermaid_code
            }
        )

    tools.append(visualize_graph)

    return tools
