from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services import auth as auth_service


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


def test_login_locks_account_after_too_many_failed_attempts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_MAX_FAILED_ATTEMPTS", "3")
    monkeypatch.setenv("AUTH_LOCKOUT_MINUTES", "15")
    get_settings.cache_clear()

    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert bootstrap_response.status_code == 201

    with TestClient(client.app) as fresh_client:
        for _ in range(2):
            login_response = fresh_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrongpassword"},
            )
            assert login_response.status_code == 401
            assert login_response.json()["detail"] == "Invalid username or password."

        locked_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert locked_response.status_code == 429
        assert (
            locked_response.json()["detail"]
            == "Account is temporarily locked due to too many failed sign-in attempts."
        )

        correct_password_while_locked = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "supersafepassword"},
        )
        assert correct_password_while_locked.status_code == 429
        assert (
            correct_password_while_locked.json()["detail"]
            == "Account is temporarily locked due to too many failed sign-in attempts."
        )


def test_login_lockout_expires_and_resets_after_success(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_MAX_FAILED_ATTEMPTS", "2")
    monkeypatch.setenv("AUTH_LOCKOUT_MINUTES", "15")
    get_settings.cache_clear()

    now = datetime(2026, 4, 12, 12, 0, tzinfo=UTC)

    def set_now(next_now: datetime) -> None:
        nonlocal now
        now = next_now

    monkeypatch.setattr(auth_service, "utcnow", lambda: now)

    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert bootstrap_response.status_code == 201

    with TestClient(client.app) as fresh_client:
        first_failed_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert first_failed_response.status_code == 401

        set_now(datetime(2026, 4, 12, 12, 1, tzinfo=UTC))
        second_failed_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert second_failed_response.status_code == 429

        set_now(datetime(2026, 4, 12, 12, 10, tzinfo=UTC))
        still_locked_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "supersafepassword"},
        )
        assert still_locked_response.status_code == 429

        set_now(datetime(2026, 4, 12, 12, 17, tzinfo=UTC))
        unlocked_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "supersafepassword"},
        )
        assert unlocked_response.status_code == 200

        set_now(datetime(2026, 4, 12, 12, 18, tzinfo=UTC))
        failed_after_success = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert failed_after_success.status_code == 401

        set_now(datetime(2026, 4, 12, 12, 19, tzinfo=UTC))
        relocked_response = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert relocked_response.status_code == 429
