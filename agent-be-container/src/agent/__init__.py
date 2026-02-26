from typing import Annotated, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class AgentState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)

async def initial_node(state: AgentState):
    # Placeholder for any initial setup or logging
    return {}

async def intent_node(state: AgentState):
    # Placeholder for intent analysis if needed in state
    return {}

def route_intent(state: AgentState) -> Literal["hello", "echo", "llm"]:
    messages = state.messages
    if not messages:
        return "echo"

    last_message = messages[-1]
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        if "hello" in content:
            return "hello"

    return "echo"

async def hello_node(state: AgentState):
    return {"messages": [AIMessage(content="Hello there!")]}

async def echo_node(state: AgentState):
    messages = state.messages
    if not messages:
        return {}

    last_message = messages[-1]

    # Only reply to HumanMessages
    if isinstance(last_message, HumanMessage):
        return {"messages": [AIMessage(content=f"Echo: {last_message.content}")]}
    return {}

def create_agent(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("initial", initial_node)
    builder.add_node("intent", intent_node)
    builder.add_node("hello", hello_node)
    builder.add_node("echo", echo_node)

    builder.add_edge(START, "initial")
    builder.add_edge("initial", "intent")

    builder.add_conditional_edges(
        "intent",
        route_intent,
        {
            "hello": "hello",
            "echo": "echo"
        }
    )

    builder.add_edge("hello", END)
    builder.add_edge("echo", END)

    return builder.compile(checkpointer=checkpointer)
