import pytest
from src.agent.tools.generate import (
    generate_agent_store_visualization,
    AgentStoreVizInput,
)
from src.agent.structs import MFEContent
from langchain_core.runnables import RunnableConfig

from unittest.mock import patch

@pytest.mark.asyncio
async def test_generate_agent_store_visualization():
    # Mock search_agent_definitions to avoid DB connection in unit test
    with patch("src.agent.agent_store.search_agent_definitions") as mock_search, \
         patch("src.config.ServiceConfig.from_yaml_and_secrets_dir") as mock_config:
        mock_search.return_value = [
            {
                "id": "1",
                "name": "Test Agent",
                "full_content": "Content",
                "top_chunk": "Top Chunk",
                "similarity": 0.95
            }
        ]

        input_data = {
            "input": {
                "name": "store_viz",
                "title": "Agent Store Visualizer",
                "description": "Shows matches for a search term",
                "query": "finance"
            }
        }

        config = RunnableConfig()
        result = await generate_agent_store_visualization.ainvoke(input_data, config)

        assert isinstance(result, MFEContent)
        assert result.provider == "angry-agent"
        assert result.component == "./AgentStoreShowWrapper"
        assert result.content["matches"] == mock_search.return_value
