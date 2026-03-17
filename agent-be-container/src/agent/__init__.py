from typing import Annotated, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel
import httpx
from src.config import LangchainConfig
from datetime import datetime, timezone
import re
import json
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition
from .tools import get_tools, MFEContent
import logging
import uuid

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """You are a helpful AI assistant.
You have access to tools that return structured data to be displayed in beautiful Micro-Frontend (MFE) components:
1. `get_mfe_content`: Use this for general JSON data, lists, or structured stats.
2. `generate_data_visualization`: Use this whenever the user asks for a chart, graph, trend, or data visualization. You MUST provide a title and one or more datasets with (x, y) values.
3. `visualize_graph`: Returns a mermaid diagram showing the internal structure and flow of this AI agent's LangGraph. Use this when the user asks 'how do you work?', 'show me your graph', or 'what is your architecture?'.
Whenever the user asks to see structured data, JSON examples, or mentions MFEs, you MUST use these tools instead of plain text to ensure the user gets a premium visual experience.

You can also create beautiful diagrams and charts using Mermaid.js syntax. To do this, simply include a ```mermaid code block in your response. The application will automatically extract and render it beautifully.
Use Mermaid for flowcharts, sequence diagrams, gantt charts, and line/bar charts when specifically requested or when it helps visualize data."""

class AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)

def extract_mermaid(text: str) -> List[str]:
    """Extracts all mermaid diagrams from markdown code blocks."""
    pattern = r"```mermaid\s*\n(.*?)\n\s*```"
    return re.findall(pattern, text, re.DOTALL)


def _try_parse_mfe_content(content) -> MFEContent | None:
    """Attempt to parse content as MFEContent using Pydantic validation.

    Handles content in the following forms:
    - dict (e.g. from tool returning a plain dict)
    - Pydantic model instance (has model_dump)
    - JSON string, optionally wrapped in markdown code fences
    """
    if isinstance(content, dict):
        try:
            return MFEContent.model_validate(content)
        except Exception:
            return None
    elif hasattr(content, "model_dump"):
        try:
            return MFEContent.model_validate(content.model_dump())
        except Exception:
            return None
    elif isinstance(content, str):
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:-3].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:-3].strip()
        try:
            return MFEContent.model_validate_json(cleaned)
        except Exception:
            return None
    return None


async def post_process_node(state: AgentState):
    """Post-processes messages after the LLM/tool loop.

    Walks messages in reverse from the last message back to the most recent
    HumanMessage (exclusive).  For each ToolMessage it inspects the content
    to see if it can be validated as an MFEContent instance (via Pydantic).
    Detected MFE payloads and mermaid diagrams are attached to the final
    AIMessage's additional_kwargs.

    Original message content is never suppressed or removed.
    """
    messages = state.messages
    if not messages:
        return {}

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return {}

    # 1. Extract Mermaid Diagrams from the final AI content
    mermaid_diagrams = extract_mermaid(last_msg.content)

    # 2. Walk backwards through prior messages to collect MFE / mermaid data
    mfe_contents = []
    for m in reversed(messages[:-1]):
        if isinstance(m, HumanMessage):
            break

        if isinstance(m, ToolMessage):
            logger.info(f"Inspecting ToolMessage (content type={type(m.content).__name__})")

            # Extract mermaid diagrams from tool string output
            if isinstance(m.content, str):
                tool_mermaid = extract_mermaid(m.content)
                if tool_mermaid:
                    logger.info(f"Extracted {len(tool_mermaid)} mermaid diagrams from ToolMessage")
                    mermaid_diagrams.extend(tool_mermaid)

            # Try to parse as MFEContent via Pydantic validation
            mfe = _try_parse_mfe_content(m.content)
            if mfe:
                logger.info(f"Detected MFEContent: mfe={mfe.mfe}, component={mfe.component}")
                mfe_contents.append(mfe.model_dump())

    # 3. Attach extracted metadata to the final AI message
    if mermaid_diagrams:
        last_msg.additional_kwargs = last_msg.additional_kwargs or {}
        last_msg.additional_kwargs["mermaid_diagrams"] = mermaid_diagrams

    if mfe_contents:
        logger.info(f"Adding {len(mfe_contents)} MFE blocks to message metadata")
        last_msg.additional_kwargs = last_msg.additional_kwargs or {}
        last_msg.additional_kwargs["mfe_contents"] = mfe_contents

    return {"messages": [last_msg]}

async def initial_node(state: AgentState):
    """Initial setup node."""
    logger.info("Initializing agent state")
    return {}

async def intent_node(state: AgentState):
    # Placeholder for intent analysis if needed in state
    return {}

def route_intent(state: AgentState) -> Literal["hello", "echo", "image", "llm"]:
    messages = state.messages
    if not messages:
        return "echo"

    last_message = messages[-1]
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        if "hello" in content:
            return "hello"
        if any(word in content for word in ["draw", "picture", "image"]):
            return "image"

    return "llm"

async def hello_node(state: AgentState):
    return {"messages": [AIMessage(
        content="Hello there!",
        additional_kwargs={"timestamp": datetime.now(timezone.utc).isoformat()}
    )]}

async def image_node(state: AgentState):
    return {"messages": [AIMessage(
        content="Here is your image:",
        additional_kwargs={
            "image_url": "https://picsum.photos/400/300",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )]}

async def echo_node(state: AgentState):
    messages = state.messages
    if not messages:
        return {}

    last_message = messages[-1]

    # Only reply to HumanMessages
    if isinstance(last_message, HumanMessage):
        return {"messages": [AIMessage(
            content=f"Echo: {last_message.content}",
            additional_kwargs={"timestamp": datetime.now(timezone.utc).isoformat()}
        )]}
    return {}


def create_agent(llm: BaseChatModel, checkpointer=None):
    builder = StateGraph(AgentState)

    tools = get_tools(builder)
    llm_with_tools = llm.bind_tools(tools)

    async def llm_node(state: AgentState):
        from langchain_core.messages import SystemMessage
        # Prepend system message for adherence
        messages = state.messages
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_MESSAGE)] + messages

        response = await llm_with_tools.ainvoke(messages)

        # Fallback for models that return tool call JSON in content instead of tool_calls field
        if isinstance(response, AIMessage) and not response.tool_calls:
            content = response.content.strip()
            # Basic heuristic for a JSON-formatted tool call in content
            if content.startswith("{") and '"name":' in content:
                try:
                    # Strip any markdown code block markers if present
                    json_str = content
                    if json_str.startswith("```json"):
                        json_str = json_str[7:-3].strip()
                    elif json_str.startswith("```"):
                        json_str = json_str[3:-3].strip()

                    tool_data = json.loads(json_str)
                    if isinstance(tool_data, dict) and "name" in tool_data and ("arguments" in tool_data or "args" in tool_data):
                        logger.warning(f"Detected hallucinated tool call in AI content: {tool_data['name']}. Converting to native tool_call.")
                        response.tool_calls = [
                            {
                                "name": tool_data["name"],
                                "args": tool_data.get("arguments") or tool_data.get("args") or {},
                                "id": f"call_{uuid.uuid4().hex[:12]}",
                                "type": "tool_call"
                            }
                        ]
                        # Clear content to avoid doubles
                        response.content = ""
                except Exception as e:
                    logger.debug(f"Failed to parse potential tool call JSON from content: {e}")

        # Add timestamp to the AI response
        if isinstance(response, AIMessage):
            response.additional_kwargs = response.additional_kwargs or {}
            response.additional_kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()
        return {"messages": [response]}

    builder.add_node("initial", initial_node)
    builder.add_node("intent", intent_node)
    builder.add_node("hello", hello_node)
    builder.add_node("echo", echo_node)
    builder.add_node("image", image_node)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("post_process", post_process_node)

    builder.add_edge(START, "initial")
    builder.add_edge("initial", "intent")

    builder.add_conditional_edges(
        "intent",
        route_intent,
        {
            "hello": "hello",
            "echo": "echo",
            "image": "image",
            "llm": "llm",
        }
    )

    builder.add_conditional_edges(
        "llm",
        tools_condition,
        {
            "tools": "tools",
            END: "post_process",
        }
    )

    builder.add_edge("tools", "llm")
    builder.add_edge("hello", END)
    builder.add_edge("image", END)
    builder.add_edge("post_process", END)
    builder.add_edge("echo", "post_process")

    return builder.compile(checkpointer=checkpointer)

def llm_model(config: LangchainConfig):
    httpx_client = httpx.Client(verify=config.httpx_verify_ssl)

    match config.model_provider:
        case "google_genai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=config.model,
                google_api_key=config.google_api_key.get_secret_value(),
            )
        case "azure_openai":
            from langchain_openai import AzureChatOpenAI

            # https://python.langchain.com/api_reference/openai/llms/langchain_openai.llms.azure.AzureOpenAI.html#langchain_openai.llms.azure.AzureOpenAI.http_client
            model = AzureChatOpenAI(
                model=config.model,
                azure_endpoint=str(config.azure_endpoint),
                api_version=config.azure_api_version,
                api_key=config.azure_api_key.get_secret_value() if config.azure_api_key else None,
                http_client=httpx_client,
            )
        case "ollama":
            from langchain_ollama import ChatOllama

            # Using str(ollama_base_url) because it's validated as an HttpUrl object
            kwargs = {"model": config.model}
            if config.ollama_base_url:
                kwargs["base_url"] = str(config.ollama_base_url)

            model = ChatOllama(**kwargs)
        case _:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    return model
