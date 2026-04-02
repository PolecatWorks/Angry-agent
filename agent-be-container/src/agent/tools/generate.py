import logging
from typing import Any, List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from src.agent.structs import MFEContent
import uuid

logger = logging.getLogger(__name__)


class JsonInput(BaseModel):
    json_content: Any = Field(description="The JSON object to render")
    title: str = Field(description="The title of the JSON object")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=JsonInput)
async def generate_mfe_of_json(json_content: Any, title: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> MFEContent:
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
        res["id"] = uuid.uuid4().hex
    return res



class MarkdownInput(BaseModel):
    markdown_content: str = Field(description="The full markdown string to be rendered in the UI.")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=MarkdownInput)
async def generate_mfe_of_markdown(markdown_content: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> MFEContent:
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
        res["id"] = uuid.uuid4().hex
    return res


class TextInput(BaseModel):
    text_content: str = Field(description="The full plain text string to be rendered in the UI.")
    pin_to_pane: bool = Field(description="Set this to True if the user explicitly requested the visualization to be placed in the right visualization pane.")
    name: str = Field(description="A unique name for the visual element.")
    description: str = Field(description="A description for the visual element.")

@tool(args_schema=TextInput)
async def generate_mfe_of_text(text_content: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> MFEContent:
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
        res["id"] = uuid.uuid4().hex
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
async def generate_mfe_of_personal_data_form(
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
        viz_id = uuid.uuid4().hex

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
async def generate_mfe_of_mermaid(mermaid_content: str, title: str, pin_to_pane: bool, name: str, description: str, config: RunnableConfig) -> MFEContent:
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
        res["id"] = uuid.uuid4().hex
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
        res["id"] = uuid.uuid4().hex
    return res
