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
from .structs import MFEContent, MFEContainer, FollowUpQuestions, AgentState, PromptFeedback
import logging
import uuid

logger = logging.getLogger(__name__)



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



async def initial_node(state: AgentState):
    """Initial setup node."""
    logger.info("Initializing agent state")
    return {}

async def intent_node(state: AgentState):
    # Placeholder for intent analysis if needed in state
    return {}

def route_intent(state: AgentState) -> Literal["hello", "echo", "image", "llm", "learning_mode"]:
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

        # Check if user has explicitly confirmed a prompt choice from learning mode
        if getattr(last_message, "additional_kwargs", {}).get("learning_mode_bypass"):
            return "llm"

    return "llm" # default

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

    follow_up_llm_with_schema = packager_llm.with_structured_output(FollowUpQuestions, include_raw=True)
    learning_mode_llm_with_schema = packager_llm.with_structured_output(PromptFeedback, include_raw=True)


    async def learning_mode_node(state: AgentState):
        logger.info("Running Learning Mode node")

        last_human_msg = None
        for m in reversed(state.messages):
            if isinstance(m, HumanMessage):
                last_human_msg = m
                break

        if not last_human_msg:
            return {}

        system_instruction = SystemMessage(content="You are an expert prompt engineer. Analyze the user's latest prompt. Provide constructive feedback on why it is good or bad, and how it could be improved. Suggest a highly improved, specific, and context-rich version of the original prompt. Provide 1-3 alternative ways to ask the question.")

        messages = [system_instruction, last_human_msg]
        raw_response = await learning_mode_llm_with_schema.ainvoke(messages)

        if isinstance(raw_response, dict) and "parsed" in raw_response:
            feedback_data = raw_response["parsed"]
            usage = raw_response["raw"].usage_metadata if hasattr(raw_response["raw"], 'usage_metadata') else None
        else:
            feedback_data = raw_response
            usage = None

        updated_kwargs = {
            "learning_mode_feedback": feedback_data.model_dump() if hasattr(feedback_data, "model_dump") else feedback_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "packaged": True
        }

        # We don't want to show the raw JSON, so we just return a message saying we analyzed it
        # The UI will pick up learning_mode_feedback from additional_kwargs
        msg = AIMessage(
            content="I've analyzed your prompt to help you get better results. Please review my suggestions below.",
            id=str(uuid.uuid4()),
            additional_kwargs=updated_kwargs,
            usage_metadata=usage
        )
        return {"messages": [msg]}

    async def post_process_node(state: AgentState):
        """Post-processes messages after the LLM/tool loop.
        Identifies pinned visualizations from tool calls and appends a summary to the final message.
        """
        logger.info("Entering post_process_node")
        messages = state.messages
        if not messages:
            return {}

        # Find the last AIMessage to update
        last_ai_msg = None
        for m in reversed(messages):
            if isinstance(m, AIMessage):
                last_ai_msg = m
                break
        if not last_ai_msg:
            return {}

        # Process all messages since the last HumanMessage (the current turn)
        messages_since_human = []
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                break
            messages_since_human.append(m)

        new_visualizations = []
        for m in messages_since_human:
            if hasattr(m, 'tool_calls') and m.tool_calls:
                for tc in m.tool_calls:
                    if tc.get('name') == "add_visualization":
                        args = tc.get("args", {})
                        mfe_arg = args.get("mfe")
                        if mfe_arg:
                            mfe = _try_parse_mfe_content(mfe_arg)
                            if mfe:
                                 new_visualizations.append(mfe.model_dump())

        # Update the last message's metadata
        updated_kwargs = last_ai_msg.additional_kwargs.copy() if last_ai_msg.additional_kwargs else {}
        
        # Add summary for pinned visualizations to the message text
        pinned_names = [v["name"] for v in new_visualizations]
        updated_content = last_ai_msg.content or ""
        if pinned_names:
            if updated_content:
                updated_content += "\n\n"
            updated_content += "**Visualizations pinned to panel:**\n- " + "\n- ".join(pinned_names)

        # Standard metadata
        updated_kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()
        updated_kwargs["packaged"] = True

        updated_msg = AIMessage(
            content=updated_content,
            id=last_ai_msg.id,
            tool_calls=getattr(last_ai_msg, "tool_calls", []),
            additional_kwargs=updated_kwargs,
            usage_metadata=getattr(last_ai_msg, "usage_metadata", None)
        )

        return {"messages": [updated_msg]}


    async def llm_node(state: AgentState):
        visualizations = state.visualizations
        viz_context = ""
        if visualizations:
            viz_list = [v.model_dump() for v in visualizations]
            viz_json = json.dumps(viz_list, indent=2)
            viz_context = f"\n\n### Current Visualizations Pinned to Workspace (JSON):\n```json\n{viz_json}\n```"

        final_prompt = f"{main_prompt}{viz_context}"
        system_instruction = SystemMessage(content=final_prompt)
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

            updated_kwargs["packaged"] = True
            updated_kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Mermaid extraction removed as per request

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



    def route_after_llm(state: AgentState) -> Literal["tools", "post_process"]:
        if tools_condition(state) == "tools":
            return "tools"
        return "post_process"

    def route_intent_or_learning_mode(state: AgentState, config: RunnableConfig) -> Literal["hello", "echo", "image", "llm", "learning_mode"]:
        # First check standard intent routing
        intent = route_intent(state)

        # If it's a standard LLM task, check if we should intercept with learning mode
        if intent == "llm":
            learning_mode_enabled = config.get("configurable", {}).get("learning_mode_enabled", False)

            # Check if this message was explicitly sent as a bypassed/confirmed learning mode choice
            messages = state.messages
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, HumanMessage) and getattr(last_message, "additional_kwargs", {}).get("learning_mode_bypass"):
                    return "llm" # user confirmed a prompt, skip learning mode and go to LLM

            if learning_mode_enabled:
                return "learning_mode"

        return intent


    builder.add_node("initial", initial_node)
    builder.add_node("intent", intent_node)
    builder.add_node("hello", hello_node)
    builder.add_node("echo", echo_node)
    builder.add_node("image", image_node)
    builder.add_node("learning_mode", learning_mode_node)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("post_process", post_process_node)
    builder.add_node("follow_up", follow_up_node)

    builder.add_edge(START, "initial")
    builder.add_edge("initial", "intent")

    builder.add_conditional_edges(
        "intent",
        route_intent_or_learning_mode,
        {
            "hello": "hello",
            "echo": "echo",
            "image": "image",
            "llm": "llm",
            "learning_mode": "learning_mode"
        }
    )

    builder.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "tools": "tools",
            "post_process": "post_process",
        }
    )

    builder.add_edge("tools", "llm")
    builder.add_edge("hello", "post_process")
    builder.add_edge("image", "post_process")
    builder.add_edge("post_process", "follow_up")
    builder.add_edge("follow_up", END)
    builder.add_edge("echo", "post_process")
    builder.add_edge("learning_mode", END) # Stop graph after learning mode node

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
