from fastapi.testclient import TestClient

from app.main import create_app


def test_status_endpoint_returns_application_version() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/status")

    assert response.status_code == 200
    payload = response.json()

    assert payload["application"] == "Goal Tracker"
    assert payload["environment"] == "development"
    assert payload["status"] == "ok"
    assert payload["version"] == "0.1.0"
    assert "checked_at" in payload
