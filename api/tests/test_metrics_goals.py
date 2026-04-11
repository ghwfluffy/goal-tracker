from __future__ import annotations

from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def test_create_and_update_integer_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "integer",
            "unit_label": "lbs",
            "initial_integer_value": 245,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["name"] == "Weight"
    assert payload["metric_type"] == "integer"
    assert payload["latest_entry"]["integer_value"] == 245

    update_response = client.post(
        f"/api/v1/metrics/{payload['id']}/entries",
        json={"integer_value": 242},
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["latest_entry"]["integer_value"] == 242
    assert len(updated_payload["entries"]) == 2


def test_create_date_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "initial_date_value": "2026-04-10",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["metric_type"] == "date"
    assert payload["latest_entry"]["date_value"] == "2026-04-10"


def test_create_goal_with_existing_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "integer",
            "initial_integer_value": 245,
        },
    )
    assert metric_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Reach 220",
            "description": "Cut steadily over spring.",
            "start_date": "2026-04-11",
            "target_date": "2026-06-30",
            "target_value_integer": 220,
            "metric_id": metric_response.json()["id"],
        },
    )

    assert goal_response.status_code == 201
    payload = goal_response.json()
    assert payload["title"] == "Reach 220"
    assert payload["metric"]["name"] == "Weight"
    assert payload["target_value_integer"] == 220


def test_create_goal_with_inline_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Stay dry this month",
            "start_date": "2026-04-11",
            "target_date": "2026-04-30",
            "metric_id": None,
            "new_metric": {
                "name": "Last drink",
                "metric_type": "date",
                "initial_date_value": "2026-04-10",
            },
        },
    )

    assert goal_response.status_code == 201
    payload = goal_response.json()
    assert payload["metric"]["name"] == "Last drink"
    assert payload["metric"]["metric_type"] == "date"

    metrics_response = client.get("/api/v1/metrics")
    assert metrics_response.status_code == 200
    assert len(metrics_response.json()["metrics"]) == 1


def test_goals_and_metrics_are_scoped_to_current_user(client: TestClient) -> None:
    bootstrap_admin(client)

    create_code_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": "2026-05-01T00:00:00Z"},
    )
    assert create_code_response.status_code == 201

    client.post("/api/v1/auth/logout")

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "member",
            "password": "supersafepassword",
            "invitation_code": create_code_response.json()["code"],
            "is_example_data": False,
        },
    )
    assert register_response.status_code == 201

    metrics_response = client.get("/api/v1/metrics")
    goals_response = client.get("/api/v1/goals")

    assert metrics_response.status_code == 200
    assert metrics_response.json() == {"metrics": []}
    assert goals_response.status_code == 200
    assert goals_response.json() == {"goals": []}


def test_example_data_user_is_seeded_with_metrics_and_goals(client: TestClient) -> None:
    bootstrap_admin(client)

    create_code_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": "2026-05-01T00:00:00Z"},
    )
    assert create_code_response.status_code == 201

    client.post("/api/v1/auth/logout")

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "demo-user",
            "password": "supersafepassword",
            "invitation_code": create_code_response.json()["code"],
            "is_example_data": True,
        },
    )
    assert register_response.status_code == 201

    metrics_response = client.get("/api/v1/metrics")
    goals_response = client.get("/api/v1/goals")

    assert metrics_response.status_code == 200
    assert sorted(metric["name"] for metric in metrics_response.json()["metrics"]) == [
        "Example Last Drink",
        "Example Weight",
    ]
    assert goals_response.status_code == 200
    assert sorted(goal["title"] for goal in goals_response.json()["goals"]) == [
        "Reach 220 lbs",
        "Stay dry this month",
    ]
