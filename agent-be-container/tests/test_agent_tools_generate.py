import pytest
from src.agent.tools.generate import (
    generate_mfe_of_json,
    JsonInput,
    generate_mfe_of_mermaid,
    MermaidInput,
    generate_data_visualization,
    DataVizInput,
    DataViz,
    Dataset,
    DataPoint,
)
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


@pytest.mark.asyncio
async def test_generate_data_visualization_happy_path():
    # Arrange
    content = DataViz(
        title="Test Data Visualization",
        x_axis_type="linear",
        datasets=[
            Dataset(
                label="Dataset 1",
                values=[
                    DataPoint(x=1, y=10.0),
                    DataPoint(x=2, y=15.5),
                ],
                color="#FF0000",
            ),
            Dataset(
                label="Dataset 2",
                values=[
                    DataPoint(x=1, y=5.0),
                    DataPoint(x=2, y=8.0),
                ],
                color="#00FF00",
            ),
        ],
    )

    input_data = DataVizInput(
        content=content,
        name="test_data_viz",
        title="Data Viz Title",
        description="Data Viz description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_data_visualization.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./DataShowWrapper"
    # pydantic model_dump() serializes content into a dictionary
    assert result.content == content.model_dump()
    assert result.name == "test_data_viz"
    assert result.title == "Data Viz Title"
    assert result.description == "Data Viz description"
