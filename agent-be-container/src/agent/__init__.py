from typing import Annotated, List, Literal, Any
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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableConfig
from .tools import get_tools
from .structs import MFEContent, MFEContainer, FollowUpQuestions, AgentState
import logging
import uuid

logger = logging.getLogger(__name__)


def extract_mermaid(text: str) -> List[str]:
    """Extracts and cleans all mermaid diagrams from markdown code blocks."""
    if not text:
        return []

    # More flexible pattern: allow optional newlines and varying whitespace
    pattern = r"```mermaid\s*\n?(.*?)\n?\s*```"
    matches = re.findall(pattern, text, re.DOTALL)

    # Strip any HTML tags that might break rendering
    cleaned_matches = []
    for m in matches:
        cleaned = re.sub(r'<[^>]+>', '', m).strip()
        if cleaned:
            cleaned_matches.append(cleaned)

    return cleaned_matches


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

    for i, message in enumerate(state.messages):
        logger.info(f"Message {i}: {type(message)} {message}")

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return {}

    updated_messages = []

    for m in reversed(messages[:-1]):
        if isinstance(m, HumanMessage):
            break

        if isinstance(m, AIMessage):
            logger.info(f"Inspecting AIMessage (content = {m})")

            mfe = _try_parse_mfe_content(m.content)
            if mfe:
                logger.info(f"Detected MFEContent: mfe={mfe.mfe}, component={mfe.component}")
                mfe_contents.append(mfe.model_dump())

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
        additional_kwargs={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "packaged": True
        }
    )]}

async def image_node(state: AgentState):
    return {"messages": [AIMessage(
        content="Here is your image:",
        additional_kwargs={
            "image_url": "https://picsum.photos/400/300",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "packaged": True
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
            additional_kwargs={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "packaged": True
            }
        )]}
    return {}


def merge_usage_metadata(m1: dict | None, m2: Any) -> dict:
    """Combines two usage_metadata objects or dictionaries."""
    res = (m1 or {}).copy()
    if not m2:
        return res

    # helper to get value from dict or object attribute
    def get_val(obj, key):
        if isinstance(obj, dict):
            return obj.get(key, 0) or 0
        return getattr(obj, key, 0) or 0

    for key in ["input_tokens", "output_tokens", "total_tokens"]:
        res[key] = res.get(key, 0) + get_val(m2, key)
    return res

def create_agent(main_llm: BaseChatModel, packager_llm: BaseChatModel, main_prompt: str = "", packager_prompt: str = "", checkpointer=None):

    builder = StateGraph(AgentState)

    tools = get_tools(builder)
    main_llm_with_tools = main_llm.bind_tools(tools)

    # This LLM is forced to output the Pydantic model. It is used for the packager to finalise the MFE output
    packager_llm_with_mfe_container_schema = packager_llm.with_structured_output(MFEContainer, include_raw=True)
    follow_up_llm_with_schema = packager_llm.with_structured_output(FollowUpQuestions, include_raw=True)


    async def llm_node(state: AgentState):
        system_instruction = SystemMessage(content=main_prompt)
        messages = [system_instruction] + state.messages

        logger.info(f"LLM Node: Invoking LLM with {len(messages)} messages (including System Prompt)")

        response = await main_llm_with_tools.ainvoke(messages)

        logger.info(f"LLM Node: Response: {response}")

        # Coerce tool calls from content if tool_calls is empty
        if not response.tool_calls and response.content:
            content = response.content.strip()
            json_str = None

            # 1. Check for markdown code block
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            # 2. Check if content itself is JSON
            elif content.startswith("{") and content.endswith("}"):
                json_str = content
            # 3. Look for any JSON-like structure in the string
            else:
                match = re.search(r"(\{.*\})", content, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()

            if json_str:
                try:
                    tool_data = json.loads(json_str)
                    if isinstance(tool_data, dict) and "name" in tool_data:
                        # Some models use 'arguments', LangChain expects 'args'
                        args = tool_data.get("args") or tool_data.get("arguments") or {}

                        # Manually inject the tool call into the message object
                        response.tool_calls = [{
                            "name": tool_data["name"],
                            "args": args,
                            "id": f"repair_{uuid.uuid4().hex[:8]}",
                            "type": "tool_call"
                        }]
                        response.content=""
                        logger.info(f"LLM Node: Successfully coerced tool call for: {tool_data['name']}")
                except Exception as e:
                    logger.debug(f"LLM Node: Content looked like JSON but failed to parse: {e}")

        return {"messages": [response]}


    async def packager_node(state: AgentState, config: RunnableConfig):

        for i, message in enumerate(state.messages):
            logger.info(f"Message {i}: {type(message)} {message}")

        # Accumulate usage metadata from all AIMessages in THE CURRENT TURN
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        messages_since_human = []
        for m in reversed(state.messages):
            if isinstance(m, HumanMessage):
                break
            messages_since_human.append(m)

        for m in reversed(messages_since_human):
            if isinstance(m, AIMessage) and hasattr(m, 'usage_metadata') and m.usage_metadata:
                total_usage = merge_usage_metadata(total_usage, m.usage_metadata)

        system_instruction = SystemMessage(content=packager_prompt)
        relevant_history = [
            m for m in state.messages
            if isinstance(m, (HumanMessage, AIMessage, ToolMessage))
        ]
        messages = [system_instruction] + relevant_history

        # We ask it to look at the TOOL results and package them
        # Note: with include_raw=True, this returns a dict with "raw" and "parsed" keys
        raw_response = await packager_llm_with_mfe_container_schema.ainvoke(messages)

        # If include_raw=True was set successfuly, we extract from the dict
        if isinstance(raw_response, dict) and "parsed" in raw_response:
            response_mfe_container = raw_response["parsed"]
            packager_usage = raw_response["raw"].usage_metadata if hasattr(raw_response["raw"], 'usage_metadata') else None
            total_usage = merge_usage_metadata(total_usage, packager_usage)
        else:
            # Fallback if with_structured_output didn't return the expected dict structure
            response_mfe_container = raw_response

        logger.info(f"MFE packager node response: {response_mfe_container}")

        # Find the last AIMessage to update it with the packaged contents
        last_ai_message = None
        for m in reversed(state.messages):
            if isinstance(m, AIMessage):
                last_ai_message = m
                break

        if last_ai_message:
            # We return a message with the SAME ID to update it in the state history
            # This follows the add_messages reducer pattern for updates
            updated_kwargs = last_ai_message.additional_kwargs.copy() if last_ai_message.additional_kwargs else {}
            
            thread_id = config.get("configurable", {}).get("thread_id")
            inline_mfes = []
            pinned_names = []
            pinned_mfes = []

            if hasattr(response_mfe_container, "mfes") and response_mfe_container.mfes:
                for mfe in response_mfe_container.mfes:
                    if mfe.pin_to_pane:
                        name = mfe.name or "Visualization"
                        desc = mfe.description or ""
                        
                        viz_id = getattr(mfe, 'id', None)
                        if not viz_id:
                            viz_id = uuid.uuid4().hex
                            mfe.id = viz_id
                        
                        pinned_names.append(f"{name} (ID: {viz_id})")
                        pinned_mfes.append(mfe)
                    else:
                        inline_mfes.append(mfe.model_dump())

            if inline_mfes:
                updated_kwargs["mfe_contents"] = inline_mfes
            else:
                updated_kwargs.pop("mfe_contents", None)
                
            updated_kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()
            updated_kwargs["packaged"] = True

            # Extract any mermaid diagrams from the conversational content
            mermaid_diagrams = extract_mermaid(last_ai_message.content)
            if mermaid_diagrams:
                updated_kwargs["mermaid_diagrams"] = mermaid_diagrams
                logger.info(f"Packager: Extracted {len(mermaid_diagrams)} mermaid diagrams")

            # Update the message text to show what was pinned
            new_content = last_ai_message.content
            if pinned_names:
                new_content += "\n\n**Visualizations pinned to panel:**\n- " + "\n- ".join(pinned_names)

            logger.info(f"Packager: Final combined usage: {total_usage}")
            updated_msg = AIMessage(
                content=new_content,
                id=last_ai_message.id,
                tool_calls=getattr(last_ai_message, 'tool_calls', []),
                additional_kwargs=updated_kwargs,
                usage_metadata=total_usage
            )

            result = {"messages": [updated_msg]}
            if pinned_mfes:
                result["visualizations"] = pinned_mfes
                
            logger.info(f"Packager: Updating existing Turn AIMessage ID={last_ai_message.id} with packaged MFEs and metadata")
            return result

        # Fallback (should not be reached in normal flow)
        logger.warning("No AIMessage found to update in packager_node, creating new one.")

        return {
            "messages": [AIMessage(
                content="I have prepared the following components for you.",
                additional_kwargs={
                    "mfe_contents": [mfe.model_dump() for mfe in response.mfes],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "packaged": True
                }
            )]
        }

    async def follow_up_node(state: AgentState):
        logger.info("Running FollowUp Questions node")
        
        # Accumulate usage metadata from all AIMessages in THE CURRENT TURN
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        messages_since_human = []
        for m in reversed(state.messages):
            if isinstance(m, HumanMessage):
                break
            messages_since_human.append(m)

        for m in reversed(messages_since_human):
            if isinstance(m, AIMessage) and hasattr(m, 'usage_metadata') and m.usage_metadata:
                total_usage = merge_usage_metadata(total_usage, m.usage_metadata)

        system_instruction = SystemMessage(content="You are a helpful assistant. Generate exactly 3 highly relevant follow-up questions the user might ask next based on the conversation history.")
        relevant_history = [
            m for m in state.messages
            if isinstance(m, (HumanMessage, AIMessage, ToolMessage))
        ]
        messages = [system_instruction] + relevant_history
        
        raw_response = await follow_up_llm_with_schema.ainvoke(messages)
        
        if isinstance(raw_response, dict) and "parsed" in raw_response:
            response_follow_ups = raw_response["parsed"]
            follow_up_usage = raw_response["raw"].usage_metadata if hasattr(raw_response["raw"], 'usage_metadata') else None
            total_usage = merge_usage_metadata(total_usage, follow_up_usage)
        else:
            response_follow_ups = raw_response

        # Find the last AIMessage to update it with the follow up questions
        last_ai_message = None
        for m in reversed(state.messages):
            if isinstance(m, AIMessage):
                last_ai_message = m
                break

        if last_ai_message:
            updated_kwargs = last_ai_message.additional_kwargs.copy() if last_ai_message.additional_kwargs else {}
            if hasattr(response_follow_ups, "follow_up_questions") and response_follow_ups.follow_up_questions:
                updated_kwargs["follow_up_questions"] = response_follow_ups.follow_up_questions
            
            logger.info(f"FollowUp: Final combined usage: {total_usage}")
            updated_msg = AIMessage(
                content=last_ai_message.content,
                id=last_ai_message.id,
                tool_calls=getattr(last_ai_message, 'tool_calls', []),
                additional_kwargs=updated_kwargs,
                usage_metadata=total_usage
            )
            return {"messages": [updated_msg]}

        return {}


    builder.add_node("initial", initial_node)
    builder.add_node("intent", intent_node)
    builder.add_node("hello", hello_node)
    builder.add_node("echo", echo_node)
    builder.add_node("image", image_node)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("packager", packager_node)
    builder.add_node("follow_up", follow_up_node)
    # builder.add_node("post_process", post_process_node)

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
            END: "packager",
        }
    )

    builder.add_edge("tools", "llm")
    builder.add_edge("hello", END)
    builder.add_edge("image", END)
    builder.add_edge("packager", "follow_up")
    builder.add_edge("follow_up", END)
    builder.add_edge("echo", END)

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
            # kwargs = {"model": config.model}
            # if config.ollama_base_url:
            #     kwargs["base_url"] = str(config.ollama_base_url)
            #     kwargs["stop"]=["<|im_start|>", "<|im_end|>"]

            model = ChatOllama(
                model=config.model,
                base_url=str(config.ollama_base_url),
                # stop=["<|im_start|>", "<|im_end|>"]
            )
        case _:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    return model
