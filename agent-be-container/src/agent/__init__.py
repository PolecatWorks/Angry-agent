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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from .tools import get_tools
from .structs import MFEContent, MFEContainer, AgentState
import logging
import uuid

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """You are a professional UI Orchestrator.
Your goal is to assist the user by providing information and visualizing that information using Micro-Frontend (MFE) components.

### IDENTITY & TONE
- You are helpful, concise, and technical.
- You speak as a bridge between data and visual representation.

### TOOL GOVERNANCE
- You have access to tools that return structured data to be displayed in beautiful Micro-Frontend (MFE) components:
  1. `generate_mfe_of_json`: Generate a pretty rendered version of input JSON.
  2. `generate_mfe_of_markdown`: Display rendered version of markdown. Use this for poems, lists, and formatted text.
  3. `generate_mfe_of_mermaid`: Render a mermaid diagram.
  4. `generate_data_visualization`: Generates a high-quality line/bar graph for trends and comparisons.
  5. `visualize_graph`: Returns a mermaid diagram of this AI agent's LangGraph.
- If the user asks for a visualization, you MUST use the appropriate tool.
- Do not describe what a tool *would* do; execute the tool to get the actual data.

### MERMAID DIAGRAMS
- You can also create beautiful diagrams using Mermaid.js syntax. To do this, simply include a ```mermaid code block in your response. The application will automatically extract and render it beautifully.
- Use Mermaid for flowcharts, sequence diagrams, and more when it helps visualize the user's request.

### EXAMPLES
- User: "Write a short poem about space."
- AI: Calls `generate_mfe_of_markdown`.

### WORKFLOW
1. Analyze the user's request.
2. If data is needed, call the relevant tools.
3. Once you have the tool results, provide a brief summary of what you've prepared.
4. Your final response should explain to the user what they are seeing in the MFEs.

### CONSTRAINTS
- Do not hallucinate data that should come from a tool.
- If a tool fails, explain the error and offer an alternative.
- Never output raw JSON blocks in your conversational text; the system will handle the packaging.
"""

PACKAGER_SYSTEM_PROMPT = """You are a UI Content Packager.
Your goal is to convert a conversation into a sequence of MFEContent objects.

### MFE NAMING
- The 'mfe' field refers to the source where the component is defined.
- ALWAYS use 'mfe1' for components like 'MarkdownShowWrapper', 'JsonShowWrapper', 'MermaidShowWrapper', and 'DataShowWrapper'.
- DO NOT increment the 'mfe' name (e.g. 'mfe1', 'mfe2') for multiple components; they should all refer to their respective source MFE.

### STEPS:
1. Identify any helpful text descriptions the AI provided. Convert these into 'MarkdownShowWrapper' MFEs using mfe='mfe1'.
2. Identify all ToolMessage results. These results contain JSON objects that define the MFE component and its content. Convert these directly into MFEContent objects.
3. If an AI message contains a JSON block that appeared to be an attempt to call an MFE tool (but failed to use the platform's tool-calling mechanism), treat this intent as if it were a successful tool call and produce the corresponding MFEContent.
4. Maintain the logical order of the explanation. Usually: [Context Markdown] -> [Tool Data MFE] -> [Closing Summary Markdown].

EXAMPLE:
If the AI said: "Here is your poem:" followed by a `generate_mfe_of_markdown` tool call or its equivalent JSON, you should produce TWO MFEContent objects:
- One for the text "Here is your poem:" (as 'MarkdownShowWrapper' from 'mfe1')
- One for the poem itself (using 'MarkdownShowWrapper' from 'mfe1').
"""


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


def create_agent(main_llm: BaseChatModel, packager_llm: BaseChatModel, checkpointer=None):

    builder = StateGraph(AgentState)

    tools = get_tools(builder)
    main_llm_with_tools = main_llm.bind_tools(tools)

    # This LLM is forced to output the Pydantic model. It is used for the packager to finalise the MFE output
    packager_llm_with_mfe_container_schema = packager_llm.with_structured_output(MFEContainer)

    async def packager_node(state: AgentState):

        for i, message in enumerate(state.messages):
            logger.info(f"Message {i}: {type(message)} {message}")

        # Map tool names to functions for manual execution if needed
        tools_map = {t.name: t for t in tools}
        enhanced_history = []
        for m in state.messages:
            if not isinstance(m, (HumanMessage, AIMessage, ToolMessage)):
                continue
            
            enhanced_history.append(m)

            # Fallback detection for malformed tool calls in content
            if isinstance(m, AIMessage) and not m.tool_calls and m.content:
                content = m.content.strip()
                # Check for JSON block (either raw or in markdown)
                json_str = None
                if (content.startswith("{") and content.endswith("}")):
                    json_str = content
                elif content.startswith("```json"):
                    json_str = content[7:-3].strip()
                elif content.startswith("```"):
                     json_str = content[3:-3].strip()

                if json_str:
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, dict) and "name" in data and data["name"] in tools_map:
                            t_name = data["name"]
                            t_args = data.get("args") or data.get("arguments") or {}
                            t_func = tools_map[t_name]
                            
                            logger.info(f"Packager: Manually executing detected tool intent from content: {t_name}")
                            # Execute the tool function
                            # Note: t_func is a LangChain BaseTool, we call invoke()
                            res = t_func.invoke(t_args)
                            
                            # Create a ToolMessage to make it "visible" to the packager LLM
                            tool_msg = ToolMessage(
                                content=json.dumps(res.model_dump()) if hasattr(res, 'model_dump') else json.dumps(res),
                                tool_call_id=f"manual_{uuid.uuid4().hex[:8]}",
                                name=t_name
                            )
                            enhanced_history.append(tool_msg)
                    except Exception as e:
                        logger.debug(f"Packager: Failed to parse/execute tool intent: {e}")

        system_instruction = SystemMessage(content=PACKAGER_SYSTEM_PROMPT)
        messages = [system_instruction] + enhanced_history

        # We ask it to look at the history (including injected ToolMessages) and package them
        response = await packager_llm_with_mfe_container_schema.ainvoke(messages)

        logger.info(f"MFE packager node response: {response}")

        # Find the last AIMessage to update it with the packaged contents
        last_ai_message = None
        for m in reversed(state.messages):
            if isinstance(m, AIMessage):
                last_ai_message = m
                break

        if last_ai_message:
            # Prepare the updated AI message
            updated_kwargs = last_ai_message.additional_kwargs.copy() if last_ai_message.additional_kwargs else {}
            updated_kwargs["mfe_contents"] = [mfe.model_dump() for mfe in response.mfes]
            updated_kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()

            updated_msg = AIMessage(
                content=last_ai_message.content,
                # We do NOT use the same ID here if we are going to use it for a ToolMessage replacement
                # to ensure this one is appended at the end.
                additional_kwargs=updated_kwargs
            )
            
            # Find the tool messages we created in this node
            new_tool_messages = [m for m in enhanced_history if isinstance(m, ToolMessage) and m not in state.messages]
            
            if new_tool_messages:
                # To clean up history, we replace the malformed AIMessage with the first ToolMessage
                # by giving the ToolMessage the same ID.
                new_tool_messages[0].id = last_ai_message.id
                logger.info(f"Packager: Replacing malformed AI message (ID={last_ai_message.id}) with ToolMessage")
            else:
                # If no new tools were created but it was an update, we still want to update the original
                updated_msg.id = last_ai_message.id
                logger.info(f"Packager: Updating existing Turn AIMessage ID={last_ai_message.id}")

            return {"messages": new_tool_messages + [updated_msg]}

        # Fallback (should not be reached in normal flow)
        logger.warning("No AIMessage found to update in packager_node, creating new one.")

        return {
            "messages": [AIMessage(
                content="I have prepared the following components for you.",
                additional_kwargs={
                    "mfe_contents": [mfe.model_dump() for mfe in response.mfes],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )]
        }

    async def llm_node(state: AgentState):
        system_instruction = SystemMessage(content=SYSTEM_MESSAGE)
        messages = [system_instruction] + state.messages

        logger.info(f"LLM Node: Invoking LLM with {len(messages)} messages (including System Prompt)")

        response = await main_llm_with_tools.ainvoke(messages)

        return {"messages": [response]}

    builder.add_node("initial", initial_node)
    builder.add_node("intent", intent_node)
    builder.add_node("hello", hello_node)
    builder.add_node("echo", echo_node)
    builder.add_node("image", image_node)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("packager", packager_node)
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
    builder.add_edge("packager", END)
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
                stop=["<|im_start|>", "<|im_end|>"]
            )
        case _:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    return model
