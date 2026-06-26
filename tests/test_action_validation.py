from app.agent.actions import validate_action


def test_valid_calendar_event():
    action = {
        "type": "add_calendar_event",
        "title": "Clean gutters",
        "date": "recurring",
        "frequency": "yearly",
        "notes": "Every spring"
    }
    result = validate_action(action)
    assert result["valid"] is True


def test_valid_task():
    action = {
        "type": "create_task",
        "title": "Repaint deck",
        "priority": "high",
        "category": "improvement"
    }
    result = validate_action(action)
    assert result["valid"] is True


def test_valid_notification():
    action = {
        "type": "send_notification",
        "message": "Roof inspection due",
        "urgency": "normal"
    }
    result = validate_action(action)
    assert result["valid"] is True


def test_invalid_type():
    result = validate_action({"type": "nonexistent"})
    assert result["valid"] is False


def test_missing_required_field():
    action = {
        "type": "create_task",
        "priority": "high",
        "category": "maintenance"
    }
    result = validate_action(action)
    assert result["valid"] is False


def test_invalid_priority():
    action = {
        "type": "create_task",
        "title": "Fix fence",
        "priority": "super urgent",
        "category": "repair"
    }
    result = validate_action(action)
    assert result["valid"] is False


def test_defaults_applied():
    action = {
        "type": "create_task",
        "title": "Fix fence"
    }
    result = validate_action(action)
    assert result["valid"] is True
    assert result["action"]["priority"] == "medium"
    assert result["action"]["category"] == "maintenance"