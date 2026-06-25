from typing import TypedDict, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    actions: list[dict]

def create_initial_state(messages: list[BaseMessage]) -> AgentState:
    return {
        "messages": messages,
        "actions": []
    }