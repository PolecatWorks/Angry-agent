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
from .tools import get_tools
import logging
import uuid

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """You are a helpful AI assistant.
You have access to a tool `get_mfe_content` that returns structured data to be displayed in a beautiful Micro-Frontend (MFE) component.
Whenever the user asks to see structured data, JSON examples, or mentions MFEs, you MUST use the `get_mfe_content` tool.
Do not just output the JSON as text; using the tool ensures the user gets a premium visual experience."""

class AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)

def extract_mermaid(text: str) -> List[str]:
    """Extracts all mermaid diagrams from markdown code blocks."""
    pattern = r"```mermaid\s*\n(.*?)\n\s*```"
    return re.findall(pattern, text, re.DOTALL)

async def post_process_node(state: AgentState):
    """Processes the last AI message to extract metadata like diagrams."""
    messages = state.messages
    if not messages:
        return {}
    
    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage):
        # 1. Extract Mermaid Diagrams
        mermaid_diagrams = extract_mermaid(last_msg.content)
        if mermaid_diagrams:
            last_msg.additional_kwargs = last_msg.additional_kwargs or {}
            last_msg.additional_kwargs["mermaid_diagrams"] = mermaid_diagrams
        
        # 2. Extract Tool Outputs for MFE rendering
        mfe_contents = []
        # We look back in history for ToolMessages
        for m in reversed(messages[:-1]):
            if isinstance(m, ToolMessage):
                logger.info(f"Checking ToolMessage with content: {str(m.content)[:100]}...")
                content_obj = None
                if isinstance(m.content, dict):
                    content_obj = m.content
                elif isinstance(m.content, str):
                    # Clean up content if it's wrapped in triple backticks
                    cleaned_content = m.content.strip()
                    if cleaned_content.startswith("```json"):
                        cleaned_content = cleaned_content[7:-3].strip()
                    elif cleaned_content.startswith("```"):
                        cleaned_content = cleaned_content[3:-3].strip()
                    try:
                        content_obj = json.loads(cleaned_content)
                    except:
                        pass
                
                if content_obj and isinstance(content_obj, dict) and "mfe" in content_obj:
                    logger.info(f"Extracted MFE content: {content_obj.get('mfe')}")
                    mfe_contents.append(content_obj)
                else:
                    logger.warning(f"ToolMessage content was not valid MFE dict: {type(content_obj)}")
            elif isinstance(m, HumanMessage):
                break
        
        if mfe_contents:
            logger.info(f"Adding {len(mfe_contents)} MFE blocks to message metadata and suppressing text content")
            last_msg.additional_kwargs = last_msg.additional_kwargs or {}
            last_msg.additional_kwargs["mfe_contents"] = mfe_contents
            # Suppress intermediate/boilerplate text if showing an MFE
            last_msg.content = ""

        return {"messages": [last_msg]}
    return {}

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
    
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    async def llm_node(state: AgentState):
        response = await llm_with_tools.ainvoke(state.messages)
        
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
                google_api_key=config.google_api_key.get_secret_value() if config.google_api_key else None,
                system_instruction=SYSTEM_MESSAGE,
                # http_client=httpx_client,
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
