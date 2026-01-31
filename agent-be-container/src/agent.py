from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

async def echo_node(state: AgentState):
    messages = state["messages"]
    if not messages:
        return {}

    last_message = messages[-1]

    # Only reply to HumanMessages to avoid loops (though graph is linear here)
    if isinstance(last_message, HumanMessage):
        return {"messages": [AIMessage(content=f"Echo: {last_message.content}")]}
    return {}

def create_agent(checkpointer=None):
    builder = StateGraph(AgentState)
    builder.add_node("echo", echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)

    return builder.compile(checkpointer=checkpointer)
