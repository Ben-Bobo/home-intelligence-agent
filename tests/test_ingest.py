import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ingest_rejects_unsupported_file():
    fake_file = io.BytesIO(b"fake content")
    response = client.post(
        "/api/ingest",
        files={"file": ("test.xlsx", fake_file, "application/vnd.ms-excel")},
        data={"doc_type": "general"}
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_ingest_rejects_no_file():
    response = client.post("/api/ingest")
    assert response.status_code == 422