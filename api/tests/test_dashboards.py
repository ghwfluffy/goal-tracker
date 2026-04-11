from __future__ import annotations

from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def test_create_dashboards_and_switch_default(client: TestClient) -> None:
    bootstrap_admin(client)

    first_response = client.post(
        "/api/v1/dashboards",
        json={"name": "Main", "description": "Daily default"},
    )
    assert first_response.status_code == 201
    assert first_response.json()["is_default"] is True

    second_response = client.post(
        "/api/v1/dashboards",
        json={"name": "Health", "description": "Health focus"},
    )
    assert second_response.status_code == 201
    assert second_response.json()["is_default"] is False

    make_default_response = client.patch(
        f"/api/v1/dashboards/{second_response.json()['id']}",
        json={"make_default": True},
    )
    assert make_default_response.status_code == 200
    assert make_default_response.json()["is_default"] is True

    dashboards_response = client.get("/api/v1/dashboards")
    assert dashboards_response.status_code == 200
    payload = dashboards_response.json()
    assert [dashboard["name"] for dashboard in payload["dashboards"]] == ["Main", "Health"]
    assert [dashboard["is_default"] for dashboard in payload["dashboards"]] == [False, True]


def test_dashboard_widgets_include_metric_and_goal_series(client: TestClient) -> None:
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

    update_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={
            "number_value": 238.0,
            "recorded_at": "2026-04-05T12:00:00Z",
        },
    )
    assert update_response.status_code == 200

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

    dashboard_response = client.post(
        "/api/v1/dashboards",
        json={"name": "Weight Dashboard", "make_default": True},
    )
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    metric_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Weight Trend",
            "widget_type": "metric_history",
            "metric_id": metric_id,
            "rolling_window_days": 365,
        },
    )
    assert metric_widget_response.status_code == 201
    metric_widget = metric_widget_response.json()
    assert metric_widget["metric"]["name"] == "Weight"
    assert [point["number_value"] for point in metric_widget["series"]] == [250.0, 238.0]

    goal_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Cut Progress",
            "widget_type": "goal_progress",
            "goal_id": goal_id,
            "rolling_window_days": 365,
        },
    )
    assert goal_widget_response.status_code == 201
    goal_widget = goal_widget_response.json()
    assert goal_widget["goal"]["title"] == "Reach 220"
    assert goal_widget["current_progress_percent"] == 40.0
    assert goal_widget["target_met"] is False
    assert [point["progress_percent"] for point in goal_widget["series"]] == [0.0, 40.0]

    dashboards_response = client.get("/api/v1/dashboards")
    assert dashboards_response.status_code == 200
    payload = dashboards_response.json()
    assert len(payload["dashboards"]) == 1
    assert len(payload["dashboards"][0]["widgets"]) == 2
