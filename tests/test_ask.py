from tests.conftest import get_client

client = get_client()


def test_ask_missing_question():
    response = client.post("/api/ask", json={})
    assert response.status_code == 422


def test_ask_wrong_type():
    response = client.post("/api/ask", json={"question": 123})
    assert response.status_code == 422