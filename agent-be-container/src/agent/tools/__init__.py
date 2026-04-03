from langchain_core.tools import tool
import logging
import re
from langchain_core.runnables import RunnableConfig

from .mfe import (
    browse_visualizations,
    read_visualization,
    edit_visualization,
    add_visualization,
    delete_visualization
)
from .generate import (
    generate_mfe_of_markdown,
    generate_mfe_of_text,
    generate_mfe_of_json,
    generate_mfe_of_mermaid,
    generate_mfe_of_personal_data_form,
    generate_data_visualization
)

logger = logging.getLogger(__name__)

def get_tools(builder: StateGraph):
    """Returns a list of tools available for the agent."""
    tools = [
        generate_data_visualization,
        generate_mfe_of_markdown,
        generate_mfe_of_text,
        generate_mfe_of_json,
        generate_mfe_of_mermaid,
        generate_mfe_of_personal_data_form,
        browse_visualizations,
        read_visualization,
        edit_visualization,
        add_visualization,
        delete_visualization
    ]

    @tool
    def visualize_graph() -> str:
        """
        Returns a mermaid diagram as a string describing the LangGraph architecture. This describes the graph describing how the agent works.
        """

        if hasattr(builder, 'get_graph'):
            mermaid_code = builder.get_graph().draw_mermaid()
        else:
            mermaid_code = builder.compile().get_graph().draw_mermaid()

        return mermaid_code

    tools.append(visualize_graph)

    return tools
