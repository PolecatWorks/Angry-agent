import logging
from typing import Any, List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from src.agent.structs import MFEContent, MFEBase
import uuid

logger = logging.getLogger(__name__)


class JsonInput(MFEBase):
    content: Any = Field(description="The JSON object to render")

@tool()
async def generate_mfe_of_json(input: JsonInput, config: RunnableConfig) -> MFEContent:
    """
    Generate a MFEContent representing the JSON provided within input
    """
    logger.info(f"Tool generate_mfe_of_json called: {content}")

    return MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./JsonShowWrapper",
    )


class MarkdownInput(MFEBase):
    content: str = Field(description="The markdown string to be rendered")

@tool()
async def generate_mfe_of_markdown(input: MarkdownInput, config: RunnableConfig) -> MFEContent:
    """
    Generate a MFEContent representing the markdown input provided in the content variable.
    """
    logger.info(f"Tool generate_mfe_of_markdown called: {content}")

    return MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./MarkdownShowWrapper",
    )



class TextInput(MFEBase):
    content: str = Field(description="The plain text string to be rendered")

@tool()
async def generate_mfe_of_text(input: TextInput, config: RunnableConfig) -> MFEContent:
    """
    Render and display plain text in the UI.
    Use this tool for logs, raw output, or simple text that should not be interpreted as markdown.
    You can use it as preamble or description before and after more complex visualisation components.
    It only supports line wrapping and basic styling.
    """
    logger.info(f"Tool generate_mfe_of_text called: {content}")

    return MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./TextShowWrapper",
    )


class PersonalDataForm(BaseModel):
    first_name: str | None = Field(default=None, description="The customer's first name, if known.")
    last_name: str | None = Field(default=None, description="The customer's last name, if known.")
    email: str | None = Field(default=None, description="The customer's email address, if known.")
    phone_number: str | None = Field(default=None, description="The customer's phone number, if known.")
    address: str | None = Field(default=None, description="The customer's physical address, if known.")

class PersonalDataFormInput(MFEBase):
    content: PersonalDataForm = Field(description="The personal data form to be displayed in the UI")

@tool()
async def generate_mfe_of_personal_data_form(
    input: PersonalDataFormInput,
    config: RunnableConfig,
) -> MFEContent:
    """
    Generate a personal data form to be displayed in the UI.
    Use this tool when the user needs to 'fill out customer data', update personal information, or provide contact details.
    """
    logger.info(f"Tool generate_personal_data_form called")
    return MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./PersonalDataFormWrapper",
    )

class MermaidInput(MFEBase):
    content: str = Field(description="The mermaid diagram as a string")

@tool()
async def generate_mfe_of_mermaid(input: MermaidInput, config: RunnableConfig) -> MFEContent:
    """
    Generate a pretty rendered version of the input mermaid diagram.
    """
    logger.info(f"Tool generate_mfe_of_mermaid called: {content}")
    reply = MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./MermaidShowWrapper",
    )
    logger.warning(f"Tool generate_mfe_of_mermaid called: {reply}")

    return reply


class DataPoint(BaseModel):
    x: Any = Field(description="The X value (number, string, or date string)")
    y: float = Field(description="The Y value (number)")

class Dataset(BaseModel):
    label: str = Field(description="Name of the dataset")
    values: List[DataPoint] = Field(description="List of data points")
    color: str | None = Field(default=None, description="Optional CSS color hex")

class DataViz(BaseModel):
    datasets: List[Dataset] = Field(description="List of datasets to plot")
    x_axis_type: Literal["linear", "time", "band"] = Field(description="Scale type for X axis")
    title: str = Field(description="The title of the visualisation")

class DataVizInput(MFEBase):
    content: DataViz = Field(description="The data visualization to be displayed in the UI")

@tool()
async def generate_data_visualization(input: DataVizInput, config: RunnableConfig) -> MFEContent:
    """
    Generates a high-quality data visualization (line graph) in the UI.
    Use this tool when the user asks for charts, graphs, trends, or data comparisons.
    """
    logger.info(f"Tool generate_data_visualization called: {title}")
    return MFEContent(
        **input.model_dump(),
        provider="mfe1",
        component="./DataShowWrapper"
    )
