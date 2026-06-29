import json
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from app.agent.actions import AVAILABLE_ACTIONS, validate_action
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

    result = validate_action(action)

    if not result["valid"]:
        error_msg = "; ".join(result["errors"])
        logger.warning("Tool: request_action | validation failed | %s", error_msg)
        return f"Error: Action validation failed. {error_msg}. Please fix and try again."

    cleaned = result["action"]

    return f"Action submitted: {cleaned['type']} — {cleaned.get('title', cleaned.get('message', ''))}. This will be processed shortly by the automation system."


request_action = StructuredTool.from_function(
    func=_request_action,
    name="request_action",
    description=_build_description(),
    args_schema=RequestActionInput,
)