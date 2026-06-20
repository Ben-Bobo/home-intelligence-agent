AVAILABLE_ACTIONS = [
    {
        "type": "add_calendar_event",
        "description": "Add an event or recurring task to the user's Google Calendar",
        "required_fields": {
            "title": "Event title",
            "date": "Start date (ISO format) or 'recurring'",
            "frequency": "once / daily / weekly / monthly (only if recurring)",
            "notes": "Additional details"
        }
    },
    {
        "type": "create_task",
        "description": "Add a task to the user's home maintenance todo list",
        "required_fields": {
            "title": "Task description",
            "priority": "low / medium / high",
            "category": "maintenance / repair / improvement"
        }
    },
    {
        "type": "send_notification",
        "description": "Send the user an alert via Slack or email about something urgent",
        "required_fields": {
            "message": "The notification content",
            "urgency": "normal / urgent"
        }
    }
]

VALID_ACTION_TYPES = {a["type"] for a in AVAILABLE_ACTIONS}