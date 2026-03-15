from langchain_core.tools import tool
import logging

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

@tool
def generate_data_visualization(title: str, datasets: list, x_axis_type: str = "linear"):
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
    return {
        "mfe": "mfe1",
        "component": "./DataShowWrapper",
        "content": {
            "title": title,
            "datasets": datasets,
            "xType": x_axis_type
        }
    }

def get_tools():
    """Returns a list of tools available for the agent."""
    return [get_mfe_content, generate_data_visualization]
