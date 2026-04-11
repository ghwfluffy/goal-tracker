from __future__ import annotations

from fastapi.testclient import TestClient


def test_bootstrap_status_reports_when_setup_is_required(client: TestClient) -> None:
    response = client.get("/api/v1/auth/bootstrap-status")

    assert response.status_code == 200
    assert response.json() == {"bootstrap_required": True}


def test_bootstrap_creates_first_admin_and_authenticates_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["username"] == "admin"
    assert payload["user"]["is_admin"] is True
    assert "goal_tracker_session" in response.cookies

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["username"] == "admin"


def test_bootstrap_is_rejected_after_first_user_exists(client: TestClient) -> None:
    first_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "another-admin", "password": "supersafepassword"},
    )

    assert second_response.status_code == 409


def test_login_and_logout_flow(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert bootstrap_response.status_code == 201

    with TestClient(client.app) as fresh_client:
        login_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "supersafepassword"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["user"]["username"] == "admin"

        me_response = fresh_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200

        logout_response = fresh_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204

        after_logout_response = fresh_client.get("/api/v1/auth/me")
        assert after_logout_response.status_code == 401


def test_login_rejects_invalid_password(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert bootstrap_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )

    assert login_response.status_code == 401
