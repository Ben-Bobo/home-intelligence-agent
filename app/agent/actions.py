from pydantic import BaseModel, Field
from typing import Literal
from app.logger import get_logger

logger = get_logger(__name__)


class CalendarEvent(BaseModel):
    type: Literal["add_calendar_event"] = "add_calendar_event"
    title: str
    date: str
    frequency: Literal["once", "daily", "weekly", "monthly", "yearly", "semiannually"] = "once"
    notes: str = ""


class Task(BaseModel):
    type: Literal["create_task"] = "create_task"
    title: str
    priority: Literal["low", "medium", "high"] = "medium"
    category: Literal["maintenance", "repair", "improvement"] = "maintenance"


class Notification(BaseModel):
    type: Literal["send_notification"] = "send_notification"
    message: str
    urgency: Literal["normal", "urgent"] = "normal"


ACTION_MODELS = {
    "add_calendar_event": CalendarEvent,
    "create_task": Task,
    "send_notification": Notification
}

VALID_ACTION_TYPES = set(ACTION_MODELS.keys())

AVAILABLE_ACTIONS = [
    {
        "type": "add_calendar_event",
        "description": "Add an event or recurring task to the user's Google Calendar",
        "required_fields": {k: v.description or k for k, v in CalendarEvent.model_fields.items() if k != "type"}
    },
    {
        "type": "create_task",
        "description": "Add a task to the user's home maintenance todo list",
        "required_fields": {k: v.description or k for k, v in Task.model_fields.items() if k != "type"}
    },
    {
        "type": "send_notification",
        "description": "Send the user an alert via Slack or email",
        "required_fields": {k: v.description or k for k, v in Notification.model_fields.items() if k != "type"}
    }
]


def validate_action(action: dict) -> dict:
    action_type = action.get("type")

    if action_type not in ACTION_MODELS:
        return {"valid": False, "action": action, "errors": [f"Unknown action type: {action_type}"]}

    try:
        model = ACTION_MODELS[action_type]
        validated = model(**action)
        return {"valid": True, "action": validated.model_dump(), "errors": []}
    except Exception as e:
        logger.warning("Action validation failed | %s", str(e))
        return {"valid": False, "action": action, "errors": [str(e)]}