from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ask_missing_question():
    response = client.post("/api/ask", json={})
    assert response.status_code == 422


def test_ask_wrong_type():
    response = client.post("/api/ask", json={"question": 123})
    assert response.status_code == 422