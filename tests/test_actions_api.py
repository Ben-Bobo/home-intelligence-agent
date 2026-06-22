from tests.conftest import get_client
from app.queue import action_queue

client = get_client()


def setup_function():
    """Clear the queue before each test."""
    action_queue._actions.clear()


def test_pending_empty():
    response = client.get("/api/actions/pending")
    assert response.status_code == 200
    assert response.json()["actions"] == []


def test_pending_returns_actions():
    action_queue.add({"type": "add_calendar_event", "title": "Test"})
    response = client.get("/api/actions/pending")
    assert response.status_code == 200
    assert len(response.json()["actions"]) == 1


def test_complete_action():
    action_id = action_queue.add({"type": "create_task", "title": "Test"})
    response = client.post("/api/actions/complete", json={"action_id": action_id})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_complete_unknown_action():
    response = client.post("/api/actions/complete", json={"action_id": "fake-id"})
    assert response.status_code == 404


def test_history_shows_all():
    action_queue.add({"type": "add_calendar_event", "title": "First"})
    action_id = action_queue.add({"type": "create_task", "title": "Second"})
    action_queue.complete(action_id)

    response = client.get("/api/actions/history")
    assert response.status_code == 200

    actions = response.json()["actions"]
    assert len(actions) == 2

    statuses = [a["status"] for a in actions]
    assert "pending" in statuses
    assert "complete" in statuses