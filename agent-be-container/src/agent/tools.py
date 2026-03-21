from langchain_core.tools import tool
import logging
import uuid
import json

from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

from typing import Any, List, Literal
from .structs import MFEContent

async def append_visualization_to_thread(config: RunnableConfig, mfe_content: MFEContent):
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        logger.warning("No thread_id found in config; cannot append visualization.")
        return

    from src.database import get_db_pool
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # We append the MFEContent dict to the existing JSONB array
            new_vis = json.dumps([mfe_content.model_dump()])
            query = """
                UPDATE threads
                SET visualizations = visualizations || $1::jsonb
                WHERE thread_id = $2
            """
            await conn.execute(query, new_vis, thread_id)
            logger.info(f"Appended visualization {mfe_content.id} to thread {thread_id}")
    except Exception as e:
        logger.error(f"Failed to append visualization to thread {thread_id}: {e}")

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
async def generate_mfe_of_json(json_content: Any, title: str, config: RunnableConfig) -> MFEContent:
    """
    Generate a pretty rendered version of the input JSON.
    """
    logger.info(f"Tool generate_mfe_of_json called: {json_content}")
    mfe = MFEContent(
        id=str(uuid.uuid4()),
        mfe="mfe1",
        component="./JsonShowWrapper",
        content={
            "content": json_content
        }
    )
    await append_visualization_to_thread(config, mfe)
    return mfe


class MarkdownInput(BaseModel):
    markdown_content: str = Field(description="The full markdown string to be rendered in the UI.")

@tool(args_schema=MarkdownInput)
async def generate_mfe_of_markdown(markdown_content: str, config: RunnableConfig) -> MFEContent:
    """
    Render and display markdown text in the UI.
    Use this tool for ANY formatted text, headers, or lists.
    """
    logger.info(f"Tool generate_mfe_of_markdown called: {markdown_content}")
    mfe = MFEContent(
        id=str(uuid.uuid4()),
        mfe="mfe1",
        component="./MarkdownShowWrapper",
        content={
            "content": markdown_content
        }
    )
    await append_visualization_to_thread(config, mfe)
    return mfe


class TextInput(BaseModel):
    text_content: str = Field(description="The full plain text string to be rendered in the UI.")

@tool(args_schema=TextInput)
async def generate_mfe_of_text(text_content: str, config: RunnableConfig) -> MFEContent:
    """
    Render and display plain text in the UI.
    Use this tool for logs, raw output, or simple text that should not be interpreted as markdown.
    You can use it as preamble or description before and after more complex visualisation components.
    It only supports line wrapping and basic styling.
    """
    logger.info(f"Tool generate_mfe_of_text called: {text_content}")
    mfe = MFEContent(
        id=str(uuid.uuid4()),
        mfe="mfe1",
        component="./TextShowWrapper",
        content={
            "content": text_content
        }
    )
    await append_visualization_to_thread(config, mfe)
    return mfe


class MermaidInput(BaseModel):
    mermaid_content: str = Field(description="The full mermaid string to be rendered in the UI. Do not include ```mermaid ... ``` markers in the content.")
    title: str = Field(description="The title of the mermaid diagram")

@tool(args_schema=MermaidInput)
async def generate_mfe_of_mermaid(mermaid_content: str, title: str, config: RunnableConfig) -> MFEContent:
    """
    Generate a pretty rendered version of the input mermaid diagram.
    """
    logger.info(f"Tool generate_mfe_of_mermaid called: {mermaid_content}")
    mfe = MFEContent(
        id=str(uuid.uuid4()),
        mfe="mfe1",
        component="./MermaidShowWrapper",
        content={
            "title": title,
            "content": mermaid_content
        }
    )
    await append_visualization_to_thread(config, mfe)
    return mfe


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
async def generate_data_visualization(title: str, datasets: List[Dataset], config: RunnableConfig, x_axis_type: str = "linear") -> MFEContent:
    """
    Generates a high-quality data visualization (line graph) in the UI.
    Use this tool when the user asks for charts, graphs, trends, or data comparisons.
    """
    logger.info(f"Tool generate_data_visualization called: {title}")
    # Convert datasets back to dicts for the MFE
    datasets_dict = [d.model_dump() for d in datasets]
    mfe = MFEContent(
        id=str(uuid.uuid4()),
        mfe="mfe1",
        component="./DataShowWrapper",
        content={
            "title": title,
            "content": datasets_dict,
            "xType": x_axis_type
        }
    )
    await append_visualization_to_thread(config, mfe)
    return mfe

class RemoveVisualizationInput(BaseModel):
    id: str = Field(description="The unique ID of the visualization to remove")

@tool(args_schema=RemoveVisualizationInput)
async def remove_visualization(id: str, config: RunnableConfig) -> str:
    """
    Removes a visualization from the right-hand panel by its ID.
    Use this tool when the user asks to remove, delete, or hide a specific chart or visualization.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: No thread ID available."

    from src.database import get_db_pool
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # PostgreSQL jsonb path removal requires finding the index, but we can do it easier
            # by extracting, filtering in Python, and updating, or using jsonb functions.
            # Python filtering is safer for simple lists.
            row = await conn.fetchrow("SELECT visualizations FROM threads WHERE thread_id = $1", thread_id)
            if row and row["visualizations"]:
                vis_list = json.loads(row["visualizations"]) if isinstance(row["visualizations"], str) else row["visualizations"]
                new_vis_list = [v for v in vis_list if v.get("id") != id]

                await conn.execute("UPDATE threads SET visualizations = $1::jsonb WHERE thread_id = $2", json.dumps(new_vis_list), thread_id)
                return f"Successfully removed visualization {id}."
            return "Visualization not found."
    except Exception as e:
        logger.error(f"Error removing visualization {id}: {e}")
        return f"Error removing visualization: {e}"

class ReorderVisualizationsInput(BaseModel):
    ordered_ids: List[str] = Field(description="The new order of visualization IDs. Must contain all existing IDs.")

@tool(args_schema=ReorderVisualizationsInput)
async def reorder_visualizations(ordered_ids: List[str], config: RunnableConfig) -> str:
    """
    Reorders the visualizations in the right-hand panel based on a provided list of IDs.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: No thread ID available."

    from src.database import get_db_pool
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT visualizations FROM threads WHERE thread_id = $1", thread_id)
            if row and row["visualizations"]:
                vis_list = json.loads(row["visualizations"]) if isinstance(row["visualizations"], str) else row["visualizations"]
                vis_dict = {v.get("id"): v for v in vis_list if v.get("id")}

                new_vis_list = []
                for vid in ordered_ids:
                    if vid in vis_dict:
                        new_vis_list.append(vis_dict[vid])

                # Append any remaining that weren't in the ordered_ids
                for v in vis_list:
                    if v.get("id") not in ordered_ids:
                        new_vis_list.append(v)

                await conn.execute("UPDATE threads SET visualizations = $1::jsonb WHERE thread_id = $2", json.dumps(new_vis_list), thread_id)
                return "Successfully reordered visualizations."
            return "No visualizations found to reorder."
    except Exception as e:
        logger.error(f"Error reordering visualizations: {e}")
        return f"Error reordering visualizations: {e}"


@tool
async def clear_visualizations(config: RunnableConfig) -> str:
    """
    Clears all visualizations from the right-hand panel.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: No thread ID available."

    from src.database import get_db_pool
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE threads SET visualizations = '[]'::jsonb WHERE thread_id = $1", thread_id)
            return "Successfully cleared all visualizations."
    except Exception as e:
        logger.error(f"Error clearing visualizations: {e}")
        return f"Error clearing visualizations: {e}"


def get_tools(builder):
    """Returns a list of tools available for the agent."""
    # tools = [generate_mfe_of_json, generate_data_visualization]
    tools = [
        generate_data_visualization,
        generate_mfe_of_markdown,
        generate_mfe_of_text,
        generate_mfe_of_json,
        generate_mfe_of_mermaid,
        remove_visualization,
        reorder_visualizations,
        clear_visualizations
    ]

    @tool
    async def visualize_graph(config: RunnableConfig) -> MFEContent:
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

        mfe = MFEContent(
            id=str(uuid.uuid4()),
            mfe="mfe1",
            component="./MermaidShowWrapper",
            content={
                "content": mermaid_code
            }
        )
        await append_visualization_to_thread(config, mfe)
        return mfe

    tools.append(visualize_graph)

    return tools
