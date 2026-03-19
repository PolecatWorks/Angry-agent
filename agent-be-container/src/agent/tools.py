from langchain_core.tools import tool
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from typing import Any
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
    mermaid_content: str = Field(description="The full mermaid string to be rendered in the UI")
    title: str = Field(description="The title of the mermaid diagram")

@tool(args_schema=MermaidInput)
def generate_mfe_of_mermaid(mermaid_content: str, title: str) -> MFEContent:
    """
    Generate a pretty rendered version of the input mermaid diagram
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


@tool
def generate_data_visualization(title: str, datasets: list, x_axis_type: str = "linear") -> MFEContent:
    """
    Generates a high-quality data visualization (line graph) in the UI.
    Use this tool when the user asks for charts, graphs, trends, or data comparisons.
    Args:
        title: The title of the visualization.
        datasets: A list of datasets to plot. Each dataset must contain:
                  - label (str): Name of the dataset.
                  - values (list): List of {x, y} points where x is a number/string/date and y is a number.
                  - color (str, optional): CSS color hex for the line (e.g., '#6366f1').
        x_axis_type: The scale type for the X axis ('linear', 'time', or 'band'). Defaults to 'linear'.
    """
    logger.info(f"Tool generate_data_visualization called: {title}")
    return MFEContent(
        mfe="mfe1",
        component="./DataShowWrapper",
        content={
            "title": title,
            "content": datasets,
            "xType": x_axis_type
        }
    )


def get_tools(builder):
    """Returns a list of tools available for the agent."""
    # tools = [generate_mfe_of_json, generate_data_visualization]
    tools = [generate_data_visualization, generate_mfe_of_markdown, generate_mfe_of_text, generate_mfe_of_json, generate_mfe_of_mermaid]

    @tool
    def visualize_graph() -> str:
        """
        Returns a mermaid diagram showing the internal structure and flow of this AI agent's LangGraph.
        Use this when the user asks 'how do you work?', 'show me your graph', or 'what is your architecture?'.
        the respose is plain mermaid code as a string
        """
        logger.info("Tool visualize_graph called")
        # StateGraph builder doesn't have get_graph() in all versions;
        # CompiledGraph does. If it's the builder, we compile it briefly to get the graph structure.
        if hasattr(builder, 'get_graph'):
            mermaid_code = builder.get_graph().draw_mermaid()
        else:
            mermaid_code = builder.compile().get_graph().draw_mermaid()

        print("mermaid_code: ", mermaid_code)

        return mermaid_code

    tools.append(visualize_graph)

    return tools
