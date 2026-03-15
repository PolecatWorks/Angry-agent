from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
def get_mfe_content(demo_type: str = "json"):
    """
    Returns a reference to a Micro-Frontend component and some content to be injected into it.
    This tool is used to display interactive or structured content in the UI via an MFE.
    Args:
        demo_type: The type of demonstration to show (e.g., 'json', 'chart', 'stats').
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

def get_tools():
    """Returns a list of tools available for the agent."""
    return [get_mfe_content]
