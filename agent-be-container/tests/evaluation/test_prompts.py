import pytest
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from deepeval import assert_test
import os

from src.agent import create_agent, AgentState, llm_model
from src.config import ServiceConfig, LangchainConfig
import yaml
from pathlib import Path

@pytest.fixture
def mock_config():
    # Load defaults from config.yaml directly but override required fields to be safe.
    config_yaml_path = Path("config.yaml")
    config_data = {}
    if config_yaml_path.exists():
        with open(config_yaml_path) as f:
            config_data = yaml.safe_load(f)

    # Modify DB credentials to pass validation
    config_data.setdefault("persistence", {}).setdefault("db", {}).setdefault("connection", {})
    config_data["persistence"]["db"]["connection"]["username"] = "dummy"
    config_data["persistence"]["db"]["connection"]["password"] = "dummy"
    config_data["persistence"]["db"]["acquire_timeout"] = 5
    config_data.setdefault("hams", {})
    config_data["hams"]["enable"] = False
    config_data["hams"]["enable_dashboard"] = False
    config_data["hams"]["url"] = "http://localhost:8001"
    config_data["hams"]["prefix"] = "/hams"
    config_data["hams"]["checks"] = {"timeout": 1, "fails": 1, "preflights": [], "shutdowns": []}
    config_data["hams"]["shutdownDuration"] = 1
    config_data.setdefault("aiclient", {})
    config_data["aiclient"]["model_provider"] = "google_genai"
    config_data["aiclient"]["model"] = "gemini-1.5-flash"
    config_data["aiclient"]["context_length"] = 8192
    config_data["aiclient"]["google_api_key"] = os.getenv("GOOGLE_API_KEY", "dummy")

    return ServiceConfig(**config_data)

@pytest.mark.asyncio
async def test_mermaid_prime_numbers(gemini_judge, mock_config):
    """
    Test that the agent can generate a valid Mermaid diagram showing the growth
    of the first 7 prime numbers.
    """
    # 1. Define the input prompt
    prompt = "show me a mermaid diagram or that chart of growth of first 7 prime numbers"

    # 2. Get the agent instance
    config = mock_config

    llm = llm_model(config.aiclient)
    agent = create_agent(llm)

    # 3. Call the agent to get its response
    state = {"messages": [("user", prompt)]}

    # We pass empty config for the graph execution
    response_state = await agent.ainvoke(state, config={"configurable": {"thread_id": "test_thread"}})
    actual_response = response_state["messages"][-1].content

    # 4. Define the expected output characteristics (Reference answer)
    # The first 7 prime numbers are: 2, 3, 5, 7, 11, 13, 17.
    # The reference doesn't need to be exact text, but provides ground truth for the judge.
    expected_output = (
        "A valid Mermaid.js diagram (e.g., a line chart, bar chart, or graph) that explicitly "
        "plots the first 7 prime numbers: 2, 3, 5, 7, 11, 13, and 17. The response must contain "
        "a ```mermaid code block."
    )

    # 5. Define the metric using our custom Gemini judge
    # GEval is a generic evaluator that uses the LLM to score the response.
    correctness_metric = GEval(
        name="Correctness",
        criteria="Determine whether the actual output accurately follows the expected output format and rules.",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        threshold=0.7,
        model=gemini_judge,
    )

    # 6. Create the test case
    test_case = LLMTestCase(
        input=prompt,
        actual_output=actual_response,
        expected_output=expected_output
    )

    # 7. Assert the test
    assert_test(test_case, [correctness_metric])
