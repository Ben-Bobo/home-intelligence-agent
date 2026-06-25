import json
from langchain_core.messages import ToolMessage
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.agent.actions import validate_action
from app.logger import get_logger

logger = get_logger(__name__)

TOOL_MAP = {tool.name: tool for tool in ALL_TOOLS}

MAX_ITERATIONS = 5

def execute_tools_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    logger.info("Node: execute_tools | tool_calls=%d", len(tool_calls))

    tool_call_count = sum(
        1 for msg in state["messages"]
        if hasattr(msg, "tool_calls") and msg.tool_calls
    )
    if tool_call_count > MAX_ITERATIONS:
        logger.warning("Node: execute_tools | MAX_ITERATIONS reached")
        return {
            "messages": [
                ToolMessage(
                    content="Maximum tool iterations reached. Please provide a final answer with the information gathered so far.",
                    tool_call_id=tool_calls[0]["id"]
                )
            ]
        }

    results = []
    new_actions = []

    for call in tool_calls:
        tool_name = call["name"]
        tool_args = call["args"]

        logger.info("Tool call: %s | args=%s", tool_name, str(tool_args)[:100])

        tool_fn = TOOL_MAP.get(tool_name)
        if tool_fn is None:
            logger.error("Unknown tool: %s", tool_name)
            result = f"Error: Unknown tool '{tool_name}'"
        else:
            try:
                result = tool_fn.invoke(tool_args)

                # If this was a request_action, capture the validated action
                if tool_name == "request_action" and "Error" not in result:
                    try:
                        action = json.loads(tool_args["action_json"])
                        validated = validate_action(action)
                        if validated["valid"]:
                            new_actions.append(validated["action"])
                    except (json.JSONDecodeError, KeyError):
                        pass

            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, str(e))
                result = f"Error calling {tool_name}: {str(e)}"

        results.append(
            ToolMessage(
                content=str(result),
                tool_call_id=call["id"]
            )
        )

    output = {"messages": results}
    if new_actions:
        output["actions"] = state.get("actions", []) + new_actions

    return output