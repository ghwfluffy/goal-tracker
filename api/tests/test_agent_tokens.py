from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import auth as auth_routes
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.services.agent_tokens import encode_agent_token, required_agent_scope


@contextmanager
def build_agent_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PUBLIC_URL", "http://testserver")
    monkeypatch.setenv("SESSION_KEY", "test-session-key")
    monkeypatch.setenv("AUTH_MODE", "oauth")
    monkeypatch.setenv("AUTH_BASE_URL", "http://auth.example.test/auth")
    monkeypatch.setenv("AGENT_INTEGRATION_TOKEN_SECRET", "test-agent-secret")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    app = create_app(session_factory=session_factory)

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        get_settings.cache_clear()


def create_oauth_user(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> str:
    login_response = client.get("/api/v1/auth/oauth/login", follow_redirects=False)
    state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

    def fake_exchange_oauth_code(*_: object, **__: object) -> dict[str, object]:
        return {
            "sub": "central-user-1",
            "preferred_username": "owner",
            "name": "Owner",
            "is_admin": True,
        }

    monkeypatch.setattr(auth_routes, "exchange_oauth_code", fake_exchange_oauth_code)
    callback = client.get(f"/api/v1/auth/oauth/callback?code=abc&state={state}", follow_redirects=False)
    assert callback.status_code == 302
    return "central-user-1"


def test_agent_token_authenticates_scoped_goals_request(monkeypatch: pytest.MonkeyPatch) -> None:
    with build_agent_client(monkeypatch) as client:
        subject = create_oauth_user(client, monkeypatch)
        token = encode_agent_token(
            secret="test-agent-secret",
            subject=subject,
            scope="goals.list_goals",
        )

        response = client.get("/api/v1/goals", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["goals"] == []


def test_agent_scope_mapping_covers_registered_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    with build_agent_client(monkeypatch) as client:
        settings = get_settings()
        cases = [
            ("GET", "/api/v1/goals", "goals.list_goals"),
            ("POST", "/api/v1/goals", "goals.create_goal"),
            ("PATCH", "/api/v1/goals/goal-1", "goals.update_goal"),
            (
                "PATCH",
                "/api/v1/goals/goal-1/checklist-items/item-1",
                "goals.complete_checklist_item",
            ),
            ("GET", "/api/v1/metrics", "goals.list_metrics"),
            ("POST", "/api/v1/metrics", "goals.create_metric"),
            ("POST", "/api/v1/metrics/metric-1/entries", "goals.record_metric_entry"),
            ("GET", "/api/v1/notifications", "goals.list_notifications"),
            (
                "POST",
                "/api/v1/notifications/notification-1/complete",
                "goals.complete_notification",
            ),
        ]
        for method, path, expected_scope in cases:
            request = client.build_request(method, path)
            assert required_agent_scope(request, settings) == expected_scope


def test_agent_token_rejects_wrong_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    with build_agent_client(monkeypatch) as client:
        subject = create_oauth_user(client, monkeypatch)
        token = encode_agent_token(
            secret="test-agent-secret",
            subject=subject,
            scope="goals.create_goal",
        )

        response = client.get("/api/v1/goals", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401


def test_agent_token_rejects_wrong_user(monkeypatch: pytest.MonkeyPatch) -> None:
    with build_agent_client(monkeypatch) as client:
        create_oauth_user(client, monkeypatch)
        token = encode_agent_token(
            secret="test-agent-secret",
            subject="other-user",
            scope="goals.list_goals",
        )

        response = client.get("/api/v1/goals", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401


def test_agent_token_rejects_wrong_app(monkeypatch: pytest.MonkeyPatch) -> None:
    with build_agent_client(monkeypatch) as client:
        subject = create_oauth_user(client, monkeypatch)
        token = encode_agent_token(
            secret="test-agent-secret",
            subject=subject,
            scope="goals.list_goals",
            audience="budget",
        )

        response = client.get("/api/v1/goals", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
