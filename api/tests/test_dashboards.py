from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.services import goal_progress


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
    assert {
        "grid_x": metric_widget["grid_x"],
        "grid_y": metric_widget["grid_y"],
        "grid_w": metric_widget["grid_w"],
        "grid_h": metric_widget["grid_h"],
    } == {
        "grid_x": 0,
        "grid_y": 0,
        "grid_w": 6,
        "grid_h": 4,
    }
    assert {
        "mobile_grid_x": metric_widget["mobile_grid_x"],
        "mobile_grid_y": metric_widget["mobile_grid_y"],
        "mobile_grid_w": metric_widget["mobile_grid_w"],
        "mobile_grid_h": metric_widget["mobile_grid_h"],
    } == {
        "mobile_grid_x": 0,
        "mobile_grid_y": 0,
        "mobile_grid_w": 1,
        "mobile_grid_h": 4,
    }
    assert [point["number_value"] for point in metric_widget["series"]] == [250.0, 238.0]
    assert metric_widget["forecast_algorithm"] is None

    goal_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Cut Progress",
            "widget_type": "goal_progress",
            "goal_id": goal_id,
            "rolling_window_days": 365,
            "forecast_algorithm": "weighted_week_over_week",
        },
    )
    assert goal_widget_response.status_code == 201
    goal_widget = goal_widget_response.json()
    assert goal_widget["goal"]["title"] == "Reach 220"
    assert goal_widget["current_progress_percent"] == 40.0
    assert goal_widget["target_met"] is False
    assert {
        "grid_x": goal_widget["grid_x"],
        "grid_y": goal_widget["grid_y"],
        "grid_w": goal_widget["grid_w"],
        "grid_h": goal_widget["grid_h"],
    } == {
        "grid_x": 6,
        "grid_y": 0,
        "grid_w": 6,
        "grid_h": 4,
    }
    assert {
        "mobile_grid_x": goal_widget["mobile_grid_x"],
        "mobile_grid_y": goal_widget["mobile_grid_y"],
        "mobile_grid_w": goal_widget["mobile_grid_w"],
        "mobile_grid_h": goal_widget["mobile_grid_h"],
    } == {
        "mobile_grid_x": 0,
        "mobile_grid_y": 4,
        "mobile_grid_w": 1,
        "mobile_grid_h": 4,
    }
    assert [point["progress_percent"] for point in goal_widget["series"]] == [0.0, 40.0]
    assert goal_widget["rolling_window_days"] is None
    assert goal_widget["forecast_algorithm"] == "weighted_week_over_week"
    assert goal_widget["time_completion_percent"] is not None
    assert goal_widget["failure_risk_percent"] is not None

    move_widget_response = client.patch(
        f"/api/v1/dashboards/{dashboard_id}/widgets/{metric_widget['id']}",
        json={"grid_x": 0, "grid_y": 4, "grid_w": 12, "grid_h": 5},
    )
    assert move_widget_response.status_code == 200
    moved_widget = move_widget_response.json()
    assert {
        "grid_x": moved_widget["grid_x"],
        "grid_y": moved_widget["grid_y"],
        "grid_w": moved_widget["grid_w"],
        "grid_h": moved_widget["grid_h"],
    } == {
        "grid_x": 0,
        "grid_y": 4,
        "grid_w": 12,
        "grid_h": 5,
    }
    assert {
        "mobile_grid_x": moved_widget["mobile_grid_x"],
        "mobile_grid_y": moved_widget["mobile_grid_y"],
        "mobile_grid_w": moved_widget["mobile_grid_w"],
        "mobile_grid_h": moved_widget["mobile_grid_h"],
    } == {
        "mobile_grid_x": 0,
        "mobile_grid_y": 0,
        "mobile_grid_w": 1,
        "mobile_grid_h": 4,
    }

    move_mobile_widget_response = client.patch(
        f"/api/v1/dashboards/{dashboard_id}/widgets/{metric_widget['id']}",
        json={"layout_mode": "mobile", "grid_x": 0, "grid_y": 8, "grid_w": 1, "grid_h": 6},
    )
    assert move_mobile_widget_response.status_code == 200
    mobile_moved_widget = move_mobile_widget_response.json()
    assert {
        "grid_x": mobile_moved_widget["grid_x"],
        "grid_y": mobile_moved_widget["grid_y"],
        "grid_w": mobile_moved_widget["grid_w"],
        "grid_h": mobile_moved_widget["grid_h"],
    } == {
        "grid_x": 0,
        "grid_y": 4,
        "grid_w": 12,
        "grid_h": 5,
    }
    assert {
        "mobile_grid_x": mobile_moved_widget["mobile_grid_x"],
        "mobile_grid_y": mobile_moved_widget["mobile_grid_y"],
        "mobile_grid_w": mobile_moved_widget["mobile_grid_w"],
        "mobile_grid_h": mobile_moved_widget["mobile_grid_h"],
    } == {
        "mobile_grid_x": 0,
        "mobile_grid_y": 4,
        "mobile_grid_w": 1,
        "mobile_grid_h": 6,
    }

    dashboards_response = client.get("/api/v1/dashboards")
    assert dashboards_response.status_code == 200
    payload = dashboards_response.json()
    assert len(payload["dashboards"]) == 1
    assert len(payload["dashboards"][0]["widgets"]) == 2
    assert [widget["mobile_grid_y"] for widget in payload["dashboards"][0]["widgets"]] == [0, 4]


def test_mobile_widget_updates_restack_a_vertical_dashboard_layout(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 200.0,
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Mobile"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    first_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "First",
            "widget_type": "metric_summary",
            "metric_id": metric_id,
        },
    )
    assert first_widget_response.status_code == 201
    first_widget = first_widget_response.json()

    second_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Second",
            "widget_type": "metric_summary",
            "metric_id": metric_id,
        },
    )
    assert second_widget_response.status_code == 201
    second_widget = second_widget_response.json()

    assert [first_widget["mobile_grid_h"], second_widget["mobile_grid_h"]] == [1, 1]
    assert [first_widget["mobile_grid_y"], second_widget["mobile_grid_y"]] == [0, 1]

    mobile_move_response = client.patch(
        f"/api/v1/dashboards/{dashboard_id}/widgets/{second_widget['id']}",
        json={"layout_mode": "mobile", "grid_y": 0},
    )
    assert mobile_move_response.status_code == 200
    assert mobile_move_response.json()["mobile_grid_y"] == 0

    dashboards_response = client.get("/api/v1/dashboards")
    assert dashboards_response.status_code == 200
    widgets = dashboards_response.json()["dashboards"][0]["widgets"]
    assert [widget["title"] for widget in sorted(widgets, key=lambda widget: widget["mobile_grid_y"])] == [
        "Second",
        "First",
    ]
    assert [
        widget["mobile_grid_y"] for widget in sorted(widgets, key=lambda widget: widget["mobile_grid_y"])
    ] == [0, 1]


def test_date_goal_progress_widget_uses_compliance_percent(client: TestClient) -> None:
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
            "title": "No drinking window",
            "start_date": "2026-04-01",
            "target_date": "2026-04-10",
            "success_threshold_percent": 80,
            "exception_dates": ["2026-04-03"],
            "metric_id": metric_id,
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Recovery"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    goal_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Sobriety Progress",
            "widget_type": "goal_progress",
            "goal_id": goal_id,
            "rolling_window_days": 365,
        },
    )
    assert goal_widget_response.status_code == 201
    goal_widget = goal_widget_response.json()
    assert goal_widget["current_progress_percent"] == 77.78
    assert goal_widget["target_met"] is False
    assert goal_widget["forecast_algorithm"] == "simple"
    assert goal_widget["goal"]["success_threshold_percent"] == 80.0
    assert goal_widget["goal"]["exception_dates"] == ["2026-04-03"]
    assert goal_widget["series"][0]["progress_percent"] == 100.0
    assert goal_widget["series"][-1]["progress_percent"] == 77.78
    assert goal_widget["rolling_window_days"] is None
    assert goal_widget["time_completion_percent"] is not None
    assert goal_widget["failure_risk_percent"] is not None


def test_days_since_widget_requires_date_metric(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 200.0,
            "recorded_at": "2026-04-01T12:00:00Z",
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Main"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Days since weigh-in",
            "widget_type": "days_since",
            "metric_id": metric_id,
        },
    )
    assert widget_response.status_code == 422
    assert widget_response.json()["detail"] == "Days since widgets require a date metric."


def test_days_since_widget_can_be_created_for_date_metric(client: TestClient) -> None:
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

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Recovery"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Days since drink",
            "widget_type": "days_since",
            "metric_id": metric_id,
        },
    )
    assert widget_response.status_code == 201
    widget = widget_response.json()
    assert widget["widget_type"] == "days_since"
    assert widget["metric"]["metric_type"] == "date"
    assert widget["metric"]["latest_entry"]["date_value"] == "2026-04-02"
    assert widget["series"][0]["date_value"] == "2026-04-02"
    assert {
        "grid_x": widget["grid_x"],
        "grid_y": widget["grid_y"],
        "grid_w": widget["grid_w"],
        "grid_h": widget["grid_h"],
    } == {
        "grid_x": 0,
        "grid_y": 0,
        "grid_w": 4,
        "grid_h": 3,
    }


def test_goal_percent_widgets_return_schedule_and_risk_fields(client: TestClient) -> None:
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
            "number_value": 235.0,
            "recorded_at": "2026-04-10T12:00:00Z",
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

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Main"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    success_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Goal success",
            "widget_type": "goal_success_percent",
            "goal_id": goal_id,
            "rolling_window_days": 14,
        },
    )
    assert success_widget_response.status_code == 201
    success_widget = success_widget_response.json()
    assert success_widget["current_progress_percent"] == 50.0
    assert success_widget["rolling_window_days"] is None

    completion_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Goal completion",
            "widget_type": "goal_completion_percent",
            "goal_id": goal_id,
        },
    )
    assert completion_widget_response.status_code == 201
    completion_widget = completion_widget_response.json()
    assert completion_widget["time_completion_percent"] is not None
    assert completion_widget["failure_risk_percent"] is not None

    risk_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Goal risk",
            "widget_type": "goal_failure_risk",
            "goal_id": goal_id,
        },
    )
    assert risk_widget_response.status_code == 201
    risk_widget = risk_widget_response.json()
    assert risk_widget["failure_risk_percent"] is not None
    assert risk_widget["forecast_algorithm"] is None


def test_goal_time_completion_uses_profile_timezone_across_goals_and_dashboards(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        goal_progress,
        "utcnow",
        lambda: datetime(2026, 4, 12, 1, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    profile_response = client.patch(
        "/api/v1/users/me",
        json={"timezone": "America/Los_Angeles"},
    )
    assert profile_response.status_code == 200

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 245.0,
            "recorded_at": "2026-04-10T12:00:00Z",
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Reach 220",
            "start_date": "2026-04-11",
            "target_date": "2026-04-13",
            "target_value_number": 220.0,
            "metric_id": metric_id,
        },
    )
    assert goal_response.status_code == 201
    assert goal_response.json()["time_progress_percent"] == 25.0
    goal_id = goal_response.json()["id"]

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Main"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Progress",
            "widget_type": "goal_progress",
            "goal_id": goal_id,
        },
    )
    assert widget_response.status_code == 201
    assert widget_response.json()["time_completion_percent"] == 25.0
