from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.agent.nodes.execute_tools import execute_tools_node, TOOL_MAP
from app.agent.graph import should_continue


# --- should_continue routing ---

def test_should_continue_with_tool_calls():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"id": "1", "name": "web_search", "args": {"query": "test"}}]
            )
        ]
    }
    assert should_continue(state) == "execute_tools"


def test_should_continue_without_tool_calls():
    state = {
        "messages": [
            AIMessage(content="Here is your answer.", tool_calls=[])
        ]
    }
    assert should_continue(state) == "end"


def test_should_continue_no_tool_calls_attr():
    state = {
        "messages": [
            AIMessage(content="Just a plain response.")
        ]
    }
    assert should_continue(state) == "end"


# --- execute_tools_node ---

def test_execute_tools_unknown_tool():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"id": "1", "name": "nonexistent_tool", "args": {}}]
            )
        ]
    }
    result = execute_tools_node(state)
    assert len(result["messages"]) == 1
    assert "Unknown tool" in result["messages"][0].content


def test_execute_tools_max_iterations():
    # Build a message history with more than MAX_ITERATIONS tool call rounds
    messages = []
    for i in range(6):
        messages.append(
            AIMessage(
                content="",
                tool_calls=[{"id": str(i), "name": "web_search", "args": {"query": "test"}}]
            )
        )
        messages.append(
            ToolMessage(content="result", tool_call_id=str(i))
        )

    # Add one more tool call that should be blocked
    messages.append(
        AIMessage(
            content="",
            tool_calls=[{"id": "final", "name": "web_search", "args": {"query": "test"}}]
        )
    )

    state = {"messages": messages}
    result = execute_tools_node(state)
    assert "Maximum tool iterations" in result["messages"][0].content


def test_tool_map_has_all_tools():
    expected = {"search_home_docs", "web_search", "analyze_image", "request_action"}
    assert set(TOOL_MAP.keys()) == expected