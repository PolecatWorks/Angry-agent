import pytest
from src.agent.tools.generate import generate_mfe_of_json, JsonInput, generate_mfe_of_mermaid, MermaidInput, generate_mfe_of_markdown, MarkdownInput, generate_mfe_of_text, TextInput, generate_mfe_of_personal_data_form, PersonalDataForm, PersonalDataFormInput, generate_data_visualization, DataVizInput, DataViz, Dataset, DataPoint
from src.agent.structs import MFEContent
from langchain_core.runnables import RunnableConfig

@pytest.mark.asyncio
async def test_generate_mfe_of_markdown_happy_path():
    # Arrange
    content = "# Hello World\nThis is a markdown test."
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


@pytest.mark.asyncio
async def test_generate_mfe_of_text_happy_path():
    # Arrange
    content = "This is a plain text string."
    input_data = TextInput(
        content=content,
        name="test_text",
        title="Text Title",
        description="Text description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_text.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./TextShowWrapper"
    assert result.content == content
    assert result.name == "test_text"
    assert result.title == "Text Title"
    assert result.description == "Text description"


@pytest.mark.asyncio
async def test_generate_mfe_of_personal_data_form_happy_path_all_fields():
    # Arrange
    content = PersonalDataForm(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        address="123 Main St"
    )
    input_data = PersonalDataFormInput(
        content=content,
        name="test_form_all",
        title="Form Title",
        description="Form description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_personal_data_form.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./PersonalDataFormWrapper"
    assert result.content == content.model_dump()
    assert result.name == "test_form_all"
    assert result.title == "Form Title"
    assert result.description == "Form description"


@pytest.mark.asyncio
async def test_generate_mfe_of_personal_data_form_happy_path_partial_fields():
    # Arrange
    content = PersonalDataForm(
        first_name="Jane",
        email="jane.doe@example.com"
    )
    input_data = PersonalDataFormInput(
        content=content,
        name="test_form_partial",
        title="Partial Form Title",
        description="Partial Form description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_mfe_of_personal_data_form.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./PersonalDataFormWrapper"
    assert result.content == content.model_dump()
    assert result.name == "test_form_partial"
    assert result.title == "Partial Form Title"
    assert result.description == "Partial Form description"


@pytest.mark.asyncio
async def test_generate_data_visualization_happy_path():
    # Arrange
    content = DataViz(
        datasets=[
            Dataset(
                label="Dataset 1",
                values=[
                    DataPoint(x=1, y=10.0),
                    DataPoint(x=2, y=20.0)
                ],
                color="#FF0000"
            )
        ],
        x_axis_type="linear",
        title="Test Visualization"
    )
    input_data = DataVizInput(
        content=content,
        name="test_viz",
        title="Viz Title",
        description="Viz description"
    )
    config = RunnableConfig()

    # Act
    result = await generate_data_visualization.ainvoke({"input": input_data}, config)

    # Assert
    assert isinstance(result, MFEContent)
    assert result.provider == "mfe1"
    assert result.component == "./DataShowWrapper"
    assert result.content == content.model_dump()
    assert result.name == "test_viz"
    assert result.title == "Viz Title"
    assert result.description == "Viz description"


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
