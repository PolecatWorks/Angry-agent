from langchain_core.tools import tool
import logging
import re
from langchain_core.runnables import RunnableConfig

# MFE DB tools removed
from .generate import (
    generate_mfe_of_markdown,
    generate_mfe_of_text,
    generate_mfe_of_json,
    generate_mfe_of_mermaid,
    generate_mfe_of_personal_data_form,
    generate_data_visualization
)

logger = logging.getLogger(__name__)

def get_tools(builder):
    """Returns a list of tools available for the agent."""
    tools = [
        generate_data_visualization,
        generate_mfe_of_markdown,
        generate_mfe_of_text,
        generate_mfe_of_json,
        generate_mfe_of_mermaid,
        generate_mfe_of_personal_data_form
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
