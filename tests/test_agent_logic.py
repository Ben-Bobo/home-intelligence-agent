from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from app.agent.nodes.execute_tools import execute_tools_node, TOOL_MAP
from app.agent.graph import should_continue
from app.routes.ask import extract_actions


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


# --- extract_actions ---

def test_extract_actions_finds_request_action():
    messages = [
        HumanMessage(content="Add gutter cleaning to my calendar"),
        AIMessage(
            content="",
            tool_calls=[{
                "id": "1",
                "name": "request_action",
                "args": {
                    "action_json": '{"type": "add_calendar_event", "title": "Clean gutters", "frequency": "yearly"}'
                }
            }]
        ),
        ToolMessage(content="Action submitted", tool_call_id="1"),
        AIMessage(content="I've submitted the calendar event.")
    ]
    actions = extract_actions(messages)
    assert len(actions) == 1
    assert actions[0]["type"] == "add_calendar_event"
    assert actions[0]["title"] == "Clean gutters"


def test_extract_actions_ignores_other_tools():
    messages = [
        AIMessage(
            content="",
            tool_calls=[{
                "id": "1",
                "name": "web_search",
                "args": {"query": "roof repair cost"}
            }]
        ),
        ToolMessage(content="some results", tool_call_id="1"),
        AIMessage(content="Here are the costs.")
    ]
    actions = extract_actions(messages)
    assert len(actions) == 0


def test_extract_actions_handles_bad_json():
    messages = [
        AIMessage(
            content="",
            tool_calls=[{
                "id": "1",
                "name": "request_action",
                "args": {"action_json": "not valid json"}
            }]
        )
    ]
    actions = extract_actions(messages)
    assert len(actions) == 0


def test_extract_actions_multiple():
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "1",
                    "name": "request_action",
                    "args": {
                        "action_json": '{"type": "add_calendar_event", "title": "Clean gutters"}'
                    }
                },
                {
                    "id": "2",
                    "name": "request_action",
                    "args": {
                        "action_json": '{"type": "create_task", "title": "Buy gutter guards", "priority": "low", "category": "improvement"}'
                    }
                }
            ]
        )
    ]
    actions = extract_actions(messages)
    assert len(actions) == 2
    assert actions[0]["type"] == "add_calendar_event"
    assert actions[1]["type"] == "create_task"


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