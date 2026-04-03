import pytest
from src.agent.tools.generate import generate_mfe_of_json, JsonInput, generate_mfe_of_markdown, MarkdownInput
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
async def test_generate_mfe_of_markdown_happy_path():
    # Arrange
    content = "# Hello World\nThis is a markdown string."
    input_data = MarkdownInput(
        content=content,
        name="test_markdown",
        title="Markdown Title",
        description="Markdown description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_markdown.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./MarkdownShowWrapper"
    assert result.content == content
    assert result.name == "test_markdown"
    assert result.title == "Markdown Title"
    assert result.description == "Markdown description"
