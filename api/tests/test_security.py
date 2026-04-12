from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.security import BCRYPT_ROUNDS, hash_password, verify_password


def test_hash_password_uses_bcrypt() -> None:
    hashed_password = hash_password("supersafepassword")

    assert hashed_password.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")
    assert verify_password("supersafepassword", hashed_password) is True
    assert verify_password("wrongpassword", hashed_password) is False


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def create_member_client(client: TestClient) -> TestClient:
    invitation_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat()},
    )
    assert invitation_response.status_code == 201

    member_client = TestClient(client.app)
    register_response = member_client.post(
        "/api/v1/auth/register",
        json={
            "username": "member",
            "password": "supersafepassword",
            "invitation_code": invitation_response.json()["code"],
            "is_example_data": False,
        },
    )
    assert register_response.status_code == 201
    return member_client


def test_user_crud_routes_reject_other_users_resources(client: TestClient) -> None:
    bootstrap_admin(client)
    member_client = create_member_client(client)

    try:
        metric_response = client.post(
            "/api/v1/metrics",
            json={
                "name": "Weight",
                "metric_type": "number",
                "decimal_places": 1,
                "initial_number_value": 250.0,
            },
        )
        assert metric_response.status_code == 201
        metric_id = metric_response.json()["id"]

        goal_response = client.post(
            "/api/v1/goals",
            json={
                "title": "Reach 220",
                "start_date": "2026-04-01",
                "target_date": "2026-06-01",
                "target_value_number": 220.0,
                "metric_id": metric_id,
            },
        )
        assert goal_response.status_code == 201
        goal_id = goal_response.json()["id"]

        dashboard_response = client.post("/api/v1/dashboards", json={"name": "Main"})
        assert dashboard_response.status_code == 201
        dashboard_id = dashboard_response.json()["id"]

        widget_response = client.post(
            f"/api/v1/dashboards/{dashboard_id}/widgets",
            json={
                "title": "Weight Trend",
                "widget_type": "metric_history",
                "metric_id": metric_id,
                "rolling_window_days": 30,
            },
        )
        assert widget_response.status_code == 201
        widget_id = widget_response.json()["id"]

        assert (
            member_client.post(
                f"/api/v1/metrics/{metric_id}/entries",
                json={"number_value": 245.0},
            ).status_code
            == 404
        )
        assert (
            member_client.patch(
                f"/api/v1/metrics/{metric_id}",
                json={"name": "Stolen metric"},
            ).status_code
            == 404
        )
        assert member_client.delete(f"/api/v1/metrics/{metric_id}").status_code == 404

        assert (
            member_client.post(
                "/api/v1/goals",
                json={
                    "title": "Use another user's metric",
                    "start_date": "2026-04-01",
                    "target_date": "2026-05-01",
                    "target_value_number": 200.0,
                    "metric_id": metric_id,
                },
            ).status_code
            == 404
        )
        assert (
            member_client.patch(
                f"/api/v1/goals/{goal_id}",
                json={"title": "Hijacked goal"},
            ).status_code
            == 404
        )

        assert (
            member_client.patch(
                f"/api/v1/dashboards/{dashboard_id}",
                json={"name": "Hijacked dashboard"},
            ).status_code
            == 404
        )
        assert member_client.delete(f"/api/v1/dashboards/{dashboard_id}").status_code == 404
        assert (
            member_client.post(
                f"/api/v1/dashboards/{dashboard_id}/widgets",
                json={
                    "title": "Unauthorized widget",
                    "widget_type": "metric_history",
                    "metric_id": metric_id,
                    "goal_id": None,
                    "rolling_window_days": 30,
                },
            ).status_code
            == 404
        )
        assert (
            member_client.patch(
                f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}",
                json={"title": "Hijacked widget"},
            ).status_code
            == 404
        )
        assert (
            member_client.delete(f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}").status_code == 404
        )
    finally:
        member_client.close()
