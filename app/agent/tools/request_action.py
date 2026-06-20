import json
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from app.agent.actions import AVAILABLE_ACTIONS, VALID_ACTION_TYPES
from app.logger import get_logger

logger = get_logger(__name__)


def _build_description() -> str:
    lines = [
        "Request an action to be executed on the user's behalf. "
        "Use this when the user asks you to add something to their calendar, "
        "create a task, or send a notification.\n",
        "Available action types:"
    ]

    for a in AVAILABLE_ACTIONS:
        fields = ", ".join(f"{k} ({v})" for k, v in a["required_fields"].items())
        lines.append(f"- {a['type']}: {a['description']}. Fields: {fields}")

    lines.append("")
    lines.append(
        'Pass a JSON string with "type" and all required fields. Example: '
        '{"type": "add_calendar_event", "title": "Check pool pH", '
        '"date": "recurring", "frequency": "weekly", "notes": "Test pH levels"}'
    )

    return "\n".join(lines)


class RequestActionInput(BaseModel):
    action_json: str = Field(description="JSON string with 'type' and all required fields for the action")


def _request_action(action_json: str) -> str:
    logger.info("Tool: request_action | input=%.100s", action_json)

    try:
        action = json.loads(action_json)
    except json.JSONDecodeError:
        return "Error: Invalid JSON. Please pass a valid JSON string."

    action_type = action.get("type")
    if action_type not in VALID_ACTION_TYPES:
        return f"Error: Unknown action type '{action_type}'. Valid types: {', '.join(VALID_ACTION_TYPES)}"

    return f"Action submitted: {action_type} — {action.get('title', action.get('message', ''))}. This will be processed shortly by the automation system."


request_action = StructuredTool.from_function(
    func=_request_action,
    name="request_action",
    description=_build_description(),
    args_schema=RequestActionInput,
)