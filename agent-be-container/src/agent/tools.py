from langchain_core.tools import tool
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)




@tool
def get_mfe_content(demo_type: str = "json"):
    """
    Returns a reference to a Micro-Frontend component and some content to be injected into it.
    This tool is used to display interactive or structured content in the UI via an MFE.
    Args:
        demo_type: The type of demonstration to show (e.g., 'json', 'chart', 'stats', 'mermaid').
    """
    logger.info("Tool get_mfe_content called")
    return {
        "mfe": "mfe1",
        "component": "./JsonShowWrapper",
        "content": {
            "name": "Initial Demonstration",
            "description": "This is a basic JSON object returned by the MFE tool.",
            "timestamp": "2026-03-15T11:58:07Z",
            "status": "success",
            "data": [
                {"id": 1, "value": "A"},
                {"id": 2, "value": "B"},
                {"id": 3, "value": "C"}
            ]
        }
    }


class MFEContent(BaseModel):
    mfe: str
    component: str
    content: dict


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
            "datasets": datasets,
            "xType": x_axis_type
        }
    ).model_dump()


def get_tools(builder=None):
    """Returns a list of tools available for the agent."""
    tools = [get_mfe_content, generate_data_visualization]
    
    if builder:
        @tool
        def visualize_graph():
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
            return f"```mermaid\n{mermaid_code}\n```"
        
        tools.append(visualize_graph)
        
    return tools
