import pytest
from src.agent.tools.generate import generate_mfe_of_json, JsonInput, generate_mfe_of_mermaid, MermaidInput
from src.agent.structs import MFEContent
from langchain_core.runnables import RunnableConfig

@pytest.mark.asyncio
async def test_generate_mfe_of_json_happy_path():
    # Arrange
    content = {"key": "value", "nested": {"key2": 123}}
    input_data = JsonInput(
        content=content,
        name="test_name",
        title="Test Title",
        description="Test description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_json.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./JsonShowWrapper"
    assert result.content == content
    assert result.name == "test_name"
    assert result.title == "Test Title"
    assert result.description == "Test description"


@pytest.mark.asyncio
async def test_generate_mfe_of_json_empty_dict():
    # Arrange
    content = {}
    input_data = JsonInput(
        content=content,
        name="test_empty",
        title="Empty Title",
        description="Empty description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_json.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./JsonShowWrapper"
    assert result.content == content
    assert result.name == "test_empty"
    assert result.title == "Empty Title"
    assert result.description == "Empty description"


@pytest.mark.asyncio
async def test_generate_mfe_of_mermaid_happy_path():
    # Arrange
    content = "graph TD; A-->B;"
    input_data = MermaidInput(
        content=content,
        name="test_mermaid",
        title="Mermaid Title",
        description="Mermaid description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_mermaid.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./MermaidShowWrapper"
    assert result.content == content
    assert result.name == "test_mermaid"
    assert result.title == "Mermaid Title"
    assert result.description == "Mermaid description"
