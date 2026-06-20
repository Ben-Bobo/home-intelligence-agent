from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import AgentState
from app.agent.nodes.reasoning import get_reasoning_node
from app.agent.nodes.execute_tools import execute_tools_node
from app.logger import get_logger

logger = get_logger(__name__)


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"

    return "end"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("reasoning", get_reasoning_node())
    graph.add_node("execute_tools", execute_tools_node)

    graph.add_edge(START, "reasoning")
    graph.add_conditional_edges(
        "reasoning",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "end": END
        }
    )
    graph.add_edge("execute_tools", "reasoning")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


agent = build_graph()