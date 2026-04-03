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
