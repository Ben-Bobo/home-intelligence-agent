from app.queue import ActionQueue


def get_fresh_queue():
    return ActionQueue()


def test_add_action():
    queue = get_fresh_queue()
    action_id = queue.add({"type": "add_calendar_event", "title": "Test"})
    assert action_id is not None
    assert len(queue.get_all()) == 1


def test_pending_returns_only_pending():
    queue = get_fresh_queue()
    queue.add({"type": "add_calendar_event", "title": "First"})
    action_id = queue.add({"type": "create_task", "title": "Second"})
    queue.complete(action_id)

    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0]["type"] == "add_calendar_event"


def test_complete_marks_done():
    queue = get_fresh_queue()
    action_id = queue.add({"type": "send_notification", "message": "Test"})
    result = queue.complete(action_id)

    assert result is True
    assert queue.get_pending() == []
    assert queue.get_all()[0]["status"] == "complete"


def test_complete_unknown_id():
    queue = get_fresh_queue()
    result = queue.complete("nonexistent-id")
    assert result is False


def test_action_stores_data():
    queue = get_fresh_queue()
    queue.add({
        "type": "add_calendar_event",
        "title": "Clean gutters",
        "frequency": "yearly"
    })

    action = queue.get_all()[0]
    assert action["type"] == "add_calendar_event"
    assert action["data"]["title"] == "Clean gutters"
    assert action["data"]["frequency"] == "yearly"
    assert action["status"] == "pending"
    assert "created_at" in action
    assert "action_id" in action