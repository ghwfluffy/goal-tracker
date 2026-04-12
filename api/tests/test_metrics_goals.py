from __future__ import annotations

from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def test_create_and_update_number_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "unit_label": "lbs",
            "initial_number_value": 245.5,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["name"] == "Weight"
    assert payload["metric_type"] == "number"
    assert payload["decimal_places"] == 1
    assert payload["latest_entry"]["number_value"] == 245.5

    update_response = client.post(
        f"/api/v1/metrics/{payload['id']}/entries",
        json={"number_value": 242.3},
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["latest_entry"]["number_value"] == 242.3
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


def test_archived_metrics_are_hidden_by_default_and_can_be_included(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 245.5,
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    archive_response = client.patch(f"/api/v1/metrics/{metric_id}", json={"archived": True})
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True

    default_list_response = client.get("/api/v1/metrics")
    assert default_list_response.status_code == 200
    assert default_list_response.json() == {"metrics": []}

    archived_list_response = client.get("/api/v1/metrics?include_archived=true")
    assert archived_list_response.status_code == 200
    assert len(archived_list_response.json()["metrics"]) == 1
    assert archived_list_response.json()["metrics"][0]["is_archived"] is True


def test_archived_metrics_cannot_be_updated(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 245.5,
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    archive_response = client.patch(f"/api/v1/metrics/{metric_id}", json={"archived": True})
    assert archive_response.status_code == 200

    update_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={"number_value": 244.0},
    )
    assert update_response.status_code == 422
    assert update_response.json()["detail"] == "Archived metrics cannot be updated."


def test_create_goal_with_existing_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 245.5,
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
            "target_value_number": 220.0,
            "metric_id": metric_response.json()["id"],
        },
    )

    assert goal_response.status_code == 201
    payload = goal_response.json()
    assert payload["title"] == "Reach 220"
    assert payload["metric"]["name"] == "Weight"
    assert payload["target_value_number"] == 220.0


def test_metric_delete_requires_no_goal_or_widget_dependencies(client: TestClient) -> None:
    bootstrap_admin(client)

    standalone_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Standalone",
            "metric_type": "number",
            "decimal_places": 0,
            "initial_number_value": 10,
        },
    )
    assert standalone_metric_response.status_code == 201

    delete_standalone_response = client.delete(f"/api/v1/metrics/{standalone_metric_response.json()['id']}")
    assert delete_standalone_response.status_code == 204

    goal_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 245.5,
        },
    )
    assert goal_metric_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Reach 220",
            "start_date": "2026-04-11",
            "target_value_number": 220.0,
            "metric_id": goal_metric_response.json()["id"],
        },
    )
    assert goal_response.status_code == 201

    delete_goal_metric_response = client.delete(f"/api/v1/metrics/{goal_metric_response.json()['id']}")
    assert delete_goal_metric_response.status_code == 422
    assert delete_goal_metric_response.json()["detail"] == "Metrics linked to goals cannot be deleted."

    widget_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Steps",
            "metric_type": "number",
            "decimal_places": 0,
            "initial_number_value": 1000,
        },
    )
    assert widget_metric_response.status_code == 201

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Main"})
    assert dashboard_response.status_code == 201

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_response.json()['id']}/widgets",
        json={
            "title": "Steps history",
            "widget_type": "metric_history",
            "metric_id": widget_metric_response.json()["id"],
            "rolling_window_days": 30,
        },
    )
    assert widget_response.status_code == 201

    delete_widget_metric_response = client.delete(f"/api/v1/metrics/{widget_metric_response.json()['id']}")
    assert delete_widget_metric_response.status_code == 422
    assert (
        delete_widget_metric_response.json()["detail"]
        == "Metrics linked to dashboard widgets cannot be deleted."
    )


def test_create_goal_with_inline_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Stay dry this month",
            "start_date": "2026-04-11",
            "target_date": "2026-04-30",
            "success_threshold_percent": 80,
            "exception_dates": ["2026-04-28"],
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
    assert payload["success_threshold_percent"] == 80.0
    assert payload["exception_dates"] == ["2026-04-28"]

    metrics_response = client.get("/api/v1/metrics")
    assert metrics_response.status_code == 200
    assert len(metrics_response.json()["metrics"]) == 1


def test_date_metric_goal_uses_exception_dates_and_success_threshold(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "initial_date_value": "2026-04-02",
            "recorded_at": "2026-04-02T20:00:00Z",
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    second_entry_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={
            "date_value": "2026-04-05",
            "recorded_at": "2026-04-05T20:00:00Z",
        },
    )
    assert second_entry_response.status_code == 200

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Stay dry except for one event",
            "start_date": "2026-04-01",
            "target_date": "2026-04-10",
            "success_threshold_percent": 80,
            "exception_dates": ["2026-04-03"],
            "metric_id": metric_id,
        },
    )
    assert goal_response.status_code == 201
    payload = goal_response.json()
    assert payload["target_value_date"] is None
    assert payload["target_value_number"] is None
    assert payload["success_threshold_percent"] == 80.0
    assert payload["exception_dates"] == ["2026-04-03"]
    assert payload["current_progress_percent"] == 77.78
    assert payload["time_progress_percent"] is not None
    assert payload["failure_risk_percent"] is not None
    assert payload["target_met"] is False


def test_number_metric_goal_includes_progress_and_failure_risk(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "unit_label": "lbs",
            "initial_number_value": 250.0,
            "recorded_at": "2026-04-01T12:00:00Z",
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    entry_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={
            "number_value": 245.0,
            "recorded_at": "2026-04-11T12:00:00Z",
        },
    )
    assert entry_response.status_code == 200

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Reach 220 lbs",
            "start_date": "2026-04-01",
            "target_date": "2026-07-10",
            "target_value_number": 220.0,
            "metric_id": metric_id,
        },
    )
    assert goal_response.status_code == 201
    payload = goal_response.json()
    assert payload["current_progress_percent"] == 16.67
    assert payload["time_progress_percent"] is not None
    assert payload["failure_risk_percent"] is not None
    assert payload["target_met"] is False


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
