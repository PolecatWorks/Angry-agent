from langchain_core.tools import tool
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from ..config import DbOptionsConfig
except (ImportError, ValueError):
    from src.config import DbOptionsConfig

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
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=JsonInput)
async def generate_mfe_of_json(json_content: Any, title: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> dict:
    """
    Generate a pretty rendered version of the input JSON.
    """
    logger.info(f"Tool generate_mfe_of_json called: {json_content}")
    res = {
        "mfe": "mfe1",
        "component": "./JsonShowWrapper",
        "content": {
            "content": json_content
        },
        "pin_to_pane": pin_to_pane,
        "name": name,
        "description": description,
        "id": None
    }
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, res["mfe"], res["component"], res["content"], name, description)
            res["id"] = viz_id
    return res

class MarkdownInput(BaseModel):
    markdown_content: str = Field(description="The full markdown string to be rendered in the UI.")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=MarkdownInput)
async def generate_mfe_of_markdown(markdown_content: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> dict:
    """
    Render and display markdown text in the UI.
    Use this tool for ANY formatted text, headers, or lists.
    """
    logger.info(f"Tool generate_mfe_of_markdown called: {markdown_content}")
    res = {
        "mfe": "mfe1",
        "component": "./MarkdownShowWrapper",
        "content": {
            "content": markdown_content
        },
        "pin_to_pane": pin_to_pane,
        "name": name,
        "description": description,
        "id": None
    }
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, res["mfe"], res["component"], res["content"], name, description)
            res["id"] = viz_id
    return res

class TextInput(BaseModel):
    text_content: str = Field(description="The full plain text string to be rendered in the UI.")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=TextInput)
async def generate_mfe_of_text(text_content: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> dict:
    """
    Render and display plain text in the UI.
    Use this tool for logs, raw output, or simple text that should not be interpreted as markdown.
    You can use it as preamble or description before and after more complex visualisation components.
    It only supports line wrapping and basic styling.
    """
    logger.info(f"Tool generate_mfe_of_text called: {text_content}")
    res = {
        "mfe": "mfe1",
        "component": "./TextShowWrapper",
        "content": {
            "content": text_content
        },
        "pin_to_pane": pin_to_pane,
        "name": name,
        "description": description,
        "id": None
    }
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, res["mfe"], res["component"], res["content"], name, description)
            res["id"] = viz_id
    return res

class PersonalDataFormInput(BaseModel):
    first_name: str | None = Field(default=None, description="The customer's first name, if known.")
    last_name: str | None = Field(default=None, description="The customer's last name, if known.")
    email: str | None = Field(default=None, description="The customer's email address, if known.")
    phone_number: str | None = Field(default=None, description="The customer's phone number, if known.")
    address: str | None = Field(default=None, description="The customer's physical address, if known.")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=PersonalDataFormInput)
async def generate_personal_data_form(
    first_name: str,
    last_name: str,
    pin_to_pane: bool,
    name: str,
    description: str,
    config: RunnableConfig,
    email: str | None = None,
    phone_number: str | None = None,
    address: str | None = None
) -> MFEContent:
    """
    Generate a personal data form to be displayed in the UI.
    Use this tool when the user needs to 'fill out customer data', update personal information, or provide contact details.
    """
    logger.info(f"Tool generate_personal_data_form called")
    content = {
        "firstName": first_name or "",
        "lastName": last_name or "",
        "email": email or "",
        "phoneNumber": phone_number or "",
        "address": address or "",
        "actions": ["submit", "cancel"]
    }
    mfe = "mfe1"
    component = "./PersonalDataFormWrapper"
    
    viz_id = None
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, mfe, component, content, name, description)

    return MFEContent(
        mfe=mfe,
        component=component,
        content=content,
        pin_to_pane=pin_to_pane,
        name=name,
        description=description,
        id=viz_id
    )

class MermaidInput(BaseModel):
    mermaid_content: str = Field(description="The full mermaid string to be rendered in the UI. Do not include ```mermaid ... ``` markers in the content.")
    title: str = Field(description="The title of the mermaid diagram")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=MermaidInput)
async def generate_mfe_of_mermaid(mermaid_content: str, title: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> dict:
    """
    Generate a pretty rendered version of the input mermaid diagram.
    """
    logger.info(f"Tool generate_mfe_of_mermaid called: {mermaid_content}")
    res = {
        "mfe": "mfe1",
        "component": "./MermaidShowWrapper",
        "content": {
            "title": title,
            "content": mermaid_content
        },
        "pin_to_pane": pin_to_pane,
        "name": name,
        "description": description,
        "id": None
    }
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, res["mfe"], res["component"], res["content"], name, description)
            res["id"] = viz_id
    return res

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
    x_axis_type: Literal["linear", "time", "band"] = Field(description="Scale type for X axis")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=DataVizInput)
async def generate_data_visualization(title: str, datasets: List[Dataset], x_axis_type: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> dict:
    """
    Generates a high-quality data visualization (line graph) in the UI.
    Use this tool when the user asks for charts, graphs, trends, or data comparisons.
    """
    logger.info(f"Tool generate_data_visualization called: {title}")
    datasets_dict = [d.model_dump() for d in datasets]
    res = {
        "mfe": "mfe1",
        "component": "./DataShowWrapper",
        "content": {
            "title": title,
            "content": datasets_dict,
            "xType": x_axis_type
        },
        "pin_to_pane": pin_to_pane,
        "name": name,
        "description": description,
        "id": None
    }
    if pin_to_pane:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            viz_id = await save_visualization_to_db(thread_id, res["mfe"], res["component"], res["content"], name, description)
            res["id"] = viz_id
    return res


import json
import uuid
import re
from langchain_core.runnables import RunnableConfig
from src.database import get_db_pool

async def save_visualization_to_db(thread_id: str, mfe: str, component: str, content: dict, name: str, description: str) -> str:
    viz_id = str(uuid.uuid4())
    content_json = json.dumps(content)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get the max order_index to append
        row = await conn.fetchrow("SELECT MAX(order_index) as max_idx FROM visualizations WHERE thread_id = $1", thread_id)
        next_idx = (row["max_idx"] + 1) if row and row["max_idx"] is not None else 0

        await conn.execute(
            """
            INSERT INTO visualizations (id, thread_id, mfe, component, content, name, description, order_index)
            VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7, $8)
            """,
            viz_id, thread_id, mfe, component, content_json, name, description, next_idx
        )
    return viz_id

class CreateVisualizationInput(BaseModel):
    mfe: str = Field(description="The source MFE where the component is defined (e.g. 'mfe1')")
    component: str = Field(description="The name of the MFE component to render")
    content: dict = Field(description="The content to render in the MFE")
    name: str = Field(description="The display name or label for the visualization")
    description: str = Field(description="A description of the visualization to help keep context")

@tool(args_schema=CreateVisualizationInput)
async def create_visualization(mfe: str, component: str, content: dict, name: str, description: str, config: RunnableConfig) -> str:
    """
    Creates a new visualization for the current thread and pins it to the right pane.
    Use this when the user wants to save or build a new visualization tool or interactive component.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Error: thread_id not found in context."

    viz_id = await save_visualization_to_db(thread_id, mfe, component, content, name, description)

    logger.info(f"Tool create_visualization called: Created {viz_id} for thread {thread_id}")
    return f"Successfully created visualization with ID: {viz_id}"


class UpdateVisualizationInput(BaseModel):
    id: str = Field(description="The ID of the visualization to update")
    content: dict = Field(description="The new content for the MFE")
    name: str | None = Field(default=None, description="Optional new display name for the visualization")
    description: str | None = Field(default=None, description="Optional new description")

@tool(args_schema=UpdateVisualizationInput)
async def update_visualization(id: str, content: dict, name: str | None, description: str | None, config: RunnableConfig) -> str:
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
        generate_personal_data_form,
        create_visualization,
        update_visualization,
        delete_visualization
    ]

    @tool
    def visualize_graph() -> dict:
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

        # Clean up mermaid code: remove HTML tags that might break some mermaid renderers
        # e.g. LangGraph often adds <p> tags in labels
        mermaid_code = re.sub(r'<[^>]+>', '', mermaid_code)

        return {
            "mfe": "mfe1",
            "component": "./MermaidShowWrapper",
            "content": {
                "title": "Agent Architecture",
                "content": mermaid_code
            }
        }

    tools.append(visualize_graph)

    return tools
