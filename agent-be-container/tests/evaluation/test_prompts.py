import pytest
import os
import yaml
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from unittest.mock import patch, AsyncMock

from src.agent import create_agent, llm_model
from src.config import ServiceConfig

@pytest.fixture
def mock_config():
    # Load defaults from config.yaml directly but override required fields to be safe.
    config_yaml_path = Path("config.yaml")
    config_data = {}
    if config_yaml_path.exists():
        with open(config_yaml_path) as f:
            config_data = yaml.safe_load(f)

    # Ensure all required fields for ServiceConfig are present to avoid Pydantic validation errors
    config_data.setdefault("hams", {})
    config_data["hams"]["url"] = "http://localhost:8001"
    config_data["hams"]["prefix"] = "/hams"
    config_data["hams"]["checks"] = {
        "timeout": 1,
        "fails": 1,
        "preflights": [],
        "shutdowns": []
    }
    config_data["hams"]["shutdownDuration"] = "PT1S"
    
    config_data.setdefault("webservice", {})
    config_data["webservice"]["url"] = "http://localhost:8080"
    
    config_data.setdefault("persistence", {}).setdefault("db", {})
    config_data["persistence"]["db"].setdefault("connection", {})
    config_data["persistence"]["db"]["connection"]["url"] = "postgresql://localhost:5432/dummy"
    config_data["persistence"]["db"]["connection"]["username"] = "dummy"
    config_data["persistence"]["db"]["connection"]["password"] = "dummy"
    config_data["persistence"]["db"]["pool_size"] = 10
    config_data["persistence"]["db"]["automigrate"] = False
    config_data["persistence"]["db"]["acquire_timeout"] = 5

    config_data.setdefault("main_aiclient", {})
    config_data["main_aiclient"]["model_provider"] = "google_genai"
    config_data["main_aiclient"]["model"] = "gemini-2.0-flash"
    config_data["main_aiclient"]["context_length"] = 8192
    config_data["main_aiclient"]["google_api_key"] = os.getenv("GOOGLE_API_KEY", "dummy")
    config_data["main_aiclient"]["system_prompt"] = "Main prompt"

    config_data.setdefault("packager_aiclient", {})
    config_data["packager_aiclient"]["model_provider"] = "google_genai"
    config_data["packager_aiclient"]["model"] = "gemini-2.0-flash"
    config_data["packager_aiclient"]["context_length"] = 8192
    config_data["packager_aiclient"]["google_api_key"] = os.getenv("GOOGLE_API_KEY", "dummy")
    config_data["packager_aiclient"]["system_prompt"] = "Packager prompt"

    config_data.setdefault("embedding_client", {})
    config_data["embedding_client"]["model_provider"] = "google_genai"
    config_data["embedding_client"]["model"] = "text-embedding-004"
    config_data["embedding_client"]["google_api_key"] = os.getenv("GOOGLE_API_KEY", "dummy")

    return ServiceConfig(**config_data)

@pytest.mark.asyncio
async def test_system_prompt_adherence_mfe(mock_config):
    """
    Test that the agent follows the system prompt by using the 'get_mfe_content' tool
    when requested to show structured data or JSON.
    """
    prompt = "Show me a JSON example of a product catalog entry."
    
    llm = llm_model(mock_config.main_aiclient)
    packager_llm = llm_model(mock_config.packager_aiclient)
    agent = create_agent(
        main_llm=llm,
        packager_llm=packager_llm,
        main_prompt=mock_config.main_aiclient.system_prompt,
        packager_prompt=mock_config.packager_aiclient.system_prompt
    )
    
    state = {"messages": [HumanMessage(content=prompt)]}
    response_state = await agent.ainvoke(state, config={"configurable": {"thread_id": "test_mfe_thread"}})
    
    last_msg = response_state["messages"][-1]
    
    # Adherence Check:
    # 1. Was the MFE tool used? (packager extracts this from ToolMessages into additional_kwargs)
    assert "mfe_contents" in last_msg.additional_kwargs, "Agent failed to use get_mfe_content for JSON request"
    assert len(last_msg.additional_kwargs["mfe_contents"]) > 0
    
    # 2. Was the visual experience prioritized?
    # Note: Packager now preserves text context, but tool calls are extracted.
    # We check that the MFE is there.
    # assert last_msg.content == "", "Agent should have suppressed text content when providing an MFE"

@pytest.mark.asyncio
async def test_system_prompt_adherence_mermaid(mock_config):
    """
    Test that the agent follows the system prompt for Mermaid diagram generation.
    """
    prompt = "Create a mermaid sequence diagram showing an order fulfillment flow."
    
    llm = llm_model(mock_config.main_aiclient)
    packager_llm = llm_model(mock_config.packager_aiclient)
    agent = create_agent(
        main_llm=llm,
        packager_llm=packager_llm,
        main_prompt=mock_config.main_aiclient.system_prompt,
        packager_prompt=mock_config.packager_aiclient.system_prompt
    )
    
    state = {"messages": [HumanMessage(content=prompt)]}
    response_state = await agent.ainvoke(state, config={"configurable": {"thread_id": "test_mermaid_thread"}})
    
    last_msg = response_state["messages"][-1]
    
    # Adherence Check:
    # 1. Did it generate a mermaid diagram (either as an MFE or extracted into additional_kwargs)?
    mfe_mermaid_contents = [mfe for mfe in last_msg.additional_kwargs.get("mfe_contents", []) if mfe["component"] == "./MermaidShowWrapper"]
    
    assert len(mfe_mermaid_contents) > 0 or "mermaid_diagrams" in last_msg.additional_kwargs, "Agent failed to generate a mermaid diagram"
    
    if mfe_mermaid_contents:
        diagram_content = mfe_mermaid_contents[0]["content"]["content"].lower()
    else:
        diagram_content = last_msg.additional_kwargs["mermaid_diagrams"][0].lower()
    
    # 2. Check for typical mermaid sequence diagram keywords
    assert "sequence" in diagram_content or "participant" in diagram_content


@pytest.mark.asyncio
async def test_system_prompt_adherence_agent_state_mermaid(mock_config):
    """
    Test that when visualizing the agent state model as mermaid, 'mfe' is not 'default'.
    """
    prompt = "display a visualisation of the agent state model as a mermaid diagram"
    
    llm = llm_model(mock_config.main_aiclient)
    packager_llm = llm_model(mock_config.packager_aiclient)
    agent = create_agent(
        main_llm=llm,
        packager_llm=packager_llm,
        main_prompt=mock_config.main_aiclient.system_prompt,
        packager_prompt=mock_config.packager_aiclient.system_prompt
    )
    
    state = {"messages": [HumanMessage(content=prompt)]}
    response_state = await agent.ainvoke(state, config={"configurable": {"thread_id": "test_agent_state_thread"}})
    
    # Check visualizations in state (pinned)
    visualizations = response_state.get("visualizations", [])
    
    # Check mfes in last message (unpinned)
    last_msg = response_state["messages"][-1]
    mfe_contents = last_msg.additional_kwargs.get("mfe_contents", [])
    
    all_mfes = []
    for v in visualizations:
        all_mfes.append(v)
    for m in mfe_contents:
        all_mfes.append(m)
        
    assert len(all_mfes) > 0, f"No visualizations or MFEs found. Content: {last_msg.content}. Kwargs: {last_msg.additional_kwargs}"
    
    for viz in all_mfes:
        # If it's a dict (from mfe_contents)
        if isinstance(viz, dict):
            mfe_val = viz.get("mfe")
        else:
            mfe_val = viz.mfe
            
        assert mfe_val != "default", f"MFE attribute should not be 'default', got {mfe_val}"
        assert mfe_val == "mfe1", f"MFE attribute should be 'mfe1', got {mfe_val}"
