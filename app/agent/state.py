from typing import TypedDict, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    question: str
    image: Optional[str]
    thread_id: Optional[str]
    messages: Annotated[list[BaseMessage], add_messages]
    actions: list[dict]
    answer: str
    error: Optional[str]