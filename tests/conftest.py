import os
from fastapi.testclient import TestClient
from app.main import app

# Use the key from env, or a test default if not set
API_KEY = os.environ.get("API_SECRET_KEY", "test-key")

def get_client():
    return TestClient(app, headers={"X-API-Key": API_KEY})