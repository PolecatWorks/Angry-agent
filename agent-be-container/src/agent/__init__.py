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
        mermaid_diagrams = extract_mermaid(last_msg.content)
        if mermaid_diagrams:
            # Update additional_kwargs with extracted diagrams
            last_msg.additional_kwargs = last_msg.additional_kwargs or {}
            last_msg.additional_kwargs["mermaid_diagrams"] = mermaid_diagrams
            # Return the message with updated metadata to replace the old one (via ID matching in add_messages)
            return {"messages": [last_msg]}
    return {}

async def initial_node(state: AgentState):
    # Placeholder for any initial setup or logging
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

    async def llm_node(state: AgentState):
        response = await llm.ainvoke(state.messages)
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

    builder.add_edge("hello", END)
    builder.add_edge("image", END)
    builder.add_edge("llm", "post_process")
    builder.add_edge("echo", "post_process")
    builder.add_edge("post_process", END)

    return builder.compile(checkpointer=checkpointer)

def llm_model(config: LangchainConfig):
    httpx_client = httpx.Client(verify=config.httpx_verify_ssl)

    match config.model_provider:
        case "google_genai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=config.model,
                google_api_key=config.google_api_key.get_secret_value() if config.google_api_key else None,
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
