from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_dashboard_widgets_default_titles_to_their_subject(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Miles run",
            "metric_type": "count",
            "decimal_places": 1,
            "unit_label": "mi",
            "initial_number_value": 12.5,
        },
    )
    assert metric_response.status_code == 201
    metric_id = metric_response.json()["id"]

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Run 100 miles",
            "start_date": "2026-04-01",
            "target_date": "2026-04-30",
            "target_value_number": 100.0,
            "metric_id": metric_id,
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Running"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    metric_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "widget_type": "metric_summary",
            "metric_id": metric_id,
            "rolling_window_days": 30,
        },
    )
    assert metric_widget_response.status_code == 201
    assert metric_widget_response.json()["title"] == "Miles run"

    goal_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "widget_type": "goal_progress",
            "goal_id": goal_id,
            "rolling_window_days": 30,
        },
    )
    assert goal_widget_response.status_code == 201
    assert goal_widget_response.json()["title"] == "Run 100 miles"

    calendar_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "widget_type": "goal_calendar",
            "goal_scope": "all",
            "calendar_period": "current_month",
        },
    )
    assert calendar_widget_response.status_code == 201
    assert calendar_widget_response.json()["title"] == "All active goals"


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


def test_goal_calendar_widget_aggregates_selected_goal_day_statuses(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.goal_calendar.utcnow",
        lambda: datetime(2026, 4, 5, 18, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    cardio_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Cardio",
            "metric_type": "date",
            "update_type": "success",
            "initial_date_value": "2026-04-01",
            "recorded_at": "2026-04-01T12:00:00Z",
        },
    )
    assert cardio_metric_response.status_code == 201
    cardio_metric_id = cardio_metric_response.json()["id"]

    cardio_entry_response = client.post(
        f"/api/v1/metrics/{cardio_metric_id}/entries",
        json={
            "date_value": "2026-04-03",
            "recorded_at": "2026-04-03T12:00:00Z",
        },
    )
    assert cardio_entry_response.status_code == 200

    cardio_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Do cardio",
            "start_date": "2026-04-01",
            "target_date": "2026-04-05",
            "success_threshold_percent": 80,
            "metric_id": cardio_metric_id,
        },
    )
    assert cardio_goal_response.status_code == 201

    drink_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "update_type": "failure",
            "initial_date_value": "2026-04-02",
            "recorded_at": "2026-04-02T12:00:00Z",
        },
    )
    assert drink_metric_response.status_code == 201
    drink_metric_id = drink_metric_response.json()["id"]

    drink_entry_response = client.post(
        f"/api/v1/metrics/{drink_metric_id}/entries",
        json={
            "date_value": "2026-04-03",
            "recorded_at": "2026-04-03T12:00:00Z",
        },
    )
    assert drink_entry_response.status_code == 200

    drink_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinking",
            "start_date": "2026-04-01",
            "target_date": "2026-04-05",
            "success_threshold_percent": 80,
            "exception_dates": ["2026-04-03"],
            "metric_id": drink_metric_id,
        },
    )
    assert drink_goal_response.status_code == 201

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Calendar"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "Goal calendar",
            "widget_type": "goal_calendar",
            "goal_scope": "selected",
            "goal_ids": [
                cardio_goal_response.json()["id"],
                drink_goal_response.json()["id"],
            ],
            "calendar_period": "goal_length",
        },
    )
    assert widget_response.status_code == 201
    widget = widget_response.json()

    assert widget["goal_scope"] == "selected"
    assert widget["calendar_period"] == "goal_length"
    assert [goal["title"] for goal in widget["goals"]] == ["Do cardio", "No drinking"]
    assert widget["calendar"]["goal_count"] == 2
    assert widget["calendar"]["starts_on"] == "2026-04-01"
    assert widget["calendar"]["ends_on"] == "2026-04-05"
    assert widget["calendar"]["grid_starts_on"] == "2026-03-29"
    assert widget["calendar"]["grid_ends_on"] == "2026-04-11"

    status_by_day = {day["date"]: day["status"] for day in widget["calendar"]["days"] if day["is_in_range"]}
    assert status_by_day == {
        "2026-04-01": "pending",
        "2026-04-02": "failed",
        "2026-04-03": "warning",
        "2026-04-04": "pending",
        "2026-04-05": "pending",
    }

    details_by_day = {
        day["date"]: [
            (goal["subject"], goal["status"], goal["result_label"]) for goal in day["goal_statuses"]
        ]
        for day in widget["calendar"]["days"]
        if day["is_in_range"]
    }
    assert details_by_day["2026-04-01"] == [
        ("Cardio", "success", "Submitted"),
        ("Last drink", "pending", "Missing"),
    ]
    assert details_by_day["2026-04-02"] == [
        ("Cardio", "pending", "Missing"),
        ("Last drink", "failed", "Failed"),
    ]
    assert details_by_day["2026-04-03"] == [
        ("Cardio", "success", "Submitted"),
        ("Last drink", "warning", "Exception"),
    ]


def test_goal_calendar_widget_can_target_all_active_goals_with_rolling_period(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.goal_calendar.utcnow",
        lambda: datetime(2026, 4, 20, 12, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    first_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Cardio",
            "metric_type": "date",
            "update_type": "success",
        },
    )
    assert first_metric_response.status_code == 201

    second_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "update_type": "failure",
        },
    )
    assert second_metric_response.status_code == 201

    first_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Do cardio",
            "start_date": "2026-04-10",
            "target_date": "2026-04-25",
            "success_threshold_percent": 80,
            "metric_id": first_metric_response.json()["id"],
        },
    )
    assert first_goal_response.status_code == 201

    second_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinking",
            "start_date": "2026-04-12",
            "target_date": "2026-04-25",
            "success_threshold_percent": 80,
            "metric_id": second_metric_response.json()["id"],
        },
    )
    assert second_goal_response.status_code == 201

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "All goals"})
    assert dashboard_response.status_code == 201

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_response.json()['id']}/widgets",
        json={
            "title": "All goals calendar",
            "widget_type": "goal_calendar",
            "goal_scope": "all",
            "calendar_period": "rolling_4_weeks",
        },
    )
    assert widget_response.status_code == 201
    widget = widget_response.json()

    assert widget["goal_scope"] == "all"
    assert widget["calendar"]["goal_count"] == 2
    assert widget["calendar"]["period"] == "rolling_4_weeks"
    assert widget["calendar"]["starts_on"] == "2026-04-10"
    assert widget["calendar"]["ends_on"] == "2026-04-20"
    assert [goal["title"] for goal in widget["goals"]] == ["Do cardio", "No drinking"]


def test_goal_calendar_marks_submitted_number_goal_days_as_success(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.goal_calendar.utcnow",
        lambda: datetime(2026, 4, 14, 18, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    weight_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "initial_number_value": 220.4,
            "recorded_at": "2026-04-14T12:00:00Z",
        },
    )
    assert weight_metric_response.status_code == 201

    weight_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Log weight",
            "start_date": "2026-04-10",
            "target_date": "2026-04-30",
            "target_value_number": 210.0,
            "metric_id": weight_metric_response.json()["id"],
        },
    )
    assert weight_goal_response.status_code == 201

    monkeypatch.setattr(
        "app.services.metrics.utcnow",
        lambda: datetime(2026, 4, 14, 11, 59, tzinfo=UTC),
    )
    drink_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "update_type": "failure",
            "reminder_time_1": "12:00",
        },
    )
    assert drink_metric_response.status_code == 201

    drink_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinking",
            "start_date": "2026-04-10",
            "target_date": "2026-04-30",
            "success_threshold_percent": 80,
            "metric_id": drink_metric_response.json()["id"],
        },
    )
    assert drink_goal_response.status_code == 201

    monkeypatch.setattr(
        "app.services.notifications.utcnow",
        lambda: datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
    )
    notifications_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notifications_response.status_code == 200
    drink_notification = next(
        notification
        for notification in notifications_response.json()["notifications"]
        if notification["metric"]["id"] == drink_metric_response.json()["id"]
    )
    skip_response = client.post(f"/api/v1/notifications/{drink_notification['id']}/skip")
    assert skip_response.status_code == 200

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Calendar"})
    assert dashboard_response.status_code == 201

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_response.json()['id']}/widgets",
        json={
            "title": "Goal calendar",
            "widget_type": "goal_calendar",
            "goal_scope": "selected",
            "goal_ids": [
                weight_goal_response.json()["id"],
                drink_goal_response.json()["id"],
            ],
            "calendar_period": "current_month",
        },
    )
    assert widget_response.status_code == 201

    widget = widget_response.json()
    day_by_date = {day["date"]: day for day in widget["calendar"]["days"]}

    assert day_by_date["2026-04-14"]["status"] == "success"
    assert day_by_date["2026-04-14"]["goal_statuses"] == [
        {
            "goal_id": weight_goal_response.json()["id"],
            "subject": "Weight",
            "status": "success",
            "result_label": "Submitted",
        },
        {
            "goal_id": drink_goal_response.json()["id"],
            "subject": "Last drink",
            "status": "success",
            "result_label": "Clear",
        },
    ]
    assert day_by_date["2026-04-13"]["status"] == "pending"


def test_goal_calendar_uses_explicit_date_metric_no_submissions(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled_at = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    created_at = scheduled_at - timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.goal_calendar.utcnow",
        lambda: datetime(2026, 4, 14, 18, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    monkeypatch.setattr("app.services.metrics.utcnow", lambda: created_at)
    success_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Cardio",
            "metric_type": "date",
            "update_type": "success",
            "reminder_time_1": "12:00",
        },
    )
    assert success_metric_response.status_code == 201

    failure_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "update_type": "failure",
            "reminder_time_1": "12:00",
        },
    )
    assert failure_metric_response.status_code == 201

    success_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Do cardio",
            "start_date": "2026-04-14",
            "target_date": "2026-04-20",
            "success_threshold_percent": 80,
            "metric_id": success_metric_response.json()["id"],
        },
    )
    assert success_goal_response.status_code == 201

    failure_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinking",
            "start_date": "2026-04-14",
            "target_date": "2026-04-20",
            "success_threshold_percent": 80,
            "metric_id": failure_metric_response.json()["id"],
        },
    )
    assert failure_goal_response.status_code == 201

    monkeypatch.setattr("app.services.notifications.utcnow", lambda: scheduled_at)
    notifications_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()["notifications"]
    assert len(notifications) == 2

    cardio_notification = next(
        notification
        for notification in notifications
        if notification["metric"]["id"] == success_metric_response.json()["id"]
    )
    drink_notification = next(
        notification
        for notification in notifications
        if notification["metric"]["id"] == failure_metric_response.json()["id"]
    )

    skip_cardio_response = client.post(f"/api/v1/notifications/{cardio_notification['id']}/skip")
    assert skip_cardio_response.status_code == 200
    skip_drink_response = client.post(f"/api/v1/notifications/{drink_notification['id']}/skip")
    assert skip_drink_response.status_code == 200

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Calendar"})
    assert dashboard_response.status_code == 201

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_response.json()['id']}/widgets",
        json={
            "title": "Goal calendar",
            "widget_type": "goal_calendar",
            "goal_scope": "selected",
            "goal_ids": [
                success_goal_response.json()["id"],
                failure_goal_response.json()["id"],
            ],
            "calendar_period": "current_month",
        },
    )
    assert widget_response.status_code == 201

    day_by_date = {day["date"]: day for day in widget_response.json()["calendar"]["days"]}
    assert day_by_date["2026-04-14"]["status"] == "failed"
    assert day_by_date["2026-04-14"]["goal_statuses"] == [
        {
            "goal_id": success_goal_response.json()["id"],
            "subject": "Cardio",
            "status": "failed",
            "result_label": "Failed",
        },
        {
            "goal_id": failure_goal_response.json()["id"],
            "subject": "Last drink",
            "status": "success",
            "result_label": "Clear",
        },
    ]


def test_goal_calendar_uses_exception_dates_for_success_date_metrics(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled_at = datetime(2026, 4, 17, 18, 0, tzinfo=UTC)
    created_at = scheduled_at - timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.goal_calendar.utcnow",
        lambda: datetime(2026, 4, 18, 18, 0, tzinfo=UTC),
    )

    bootstrap_admin(client)

    monkeypatch.setattr("app.services.metrics.utcnow", lambda: created_at)
    success_metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Cardio",
            "metric_type": "date",
            "update_type": "success",
            "reminder_time_1": "18:00",
        },
    )
    assert success_metric_response.status_code == 201

    success_goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Do cardio",
            "start_date": "2026-04-13",
            "target_date": "2026-04-30",
            "success_threshold_percent": 100,
            "exception_dates": ["2026-04-17"],
            "metric_id": success_metric_response.json()["id"],
        },
    )
    assert success_goal_response.status_code == 201

    monkeypatch.setattr("app.services.notifications.utcnow", lambda: scheduled_at)
    notifications_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()["notifications"]
    assert len(notifications) == 1

    skip_response = client.post(f"/api/v1/notifications/{notifications[0]['id']}/skip")
    assert skip_response.status_code == 200

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Calendar"})
    assert dashboard_response.status_code == 201

    widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_response.json()['id']}/widgets",
        json={
            "title": "Goal calendar",
            "widget_type": "goal_calendar",
            "goal_scope": "selected",
            "goal_ids": [success_goal_response.json()["id"]],
            "calendar_period": "goal_length",
        },
    )
    assert widget_response.status_code == 201

    day_by_date = {day["date"]: day for day in widget_response.json()["calendar"]["days"]}
    assert day_by_date["2026-04-17"]["status"] == "warning"
    assert day_by_date["2026-04-17"]["goal_statuses"] == [
        {
            "goal_id": success_goal_response.json()["id"],
            "subject": "Cardio",
            "status": "warning",
            "result_label": "Exception",
        }
    ]


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


def test_checklist_goal_widgets_include_checkboxes_and_progress_series(client: TestClient) -> None:
    bootstrap_admin(client)

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "goal_type": "checklist",
            "title": "Clean house",
            "start_date": "2026-04-11",
            "target_date": "2026-04-20",
            "checklist_items": [
                {"title": "Mop floors"},
                {"title": "Do laundry"},
            ],
        },
    )
    assert goal_response.status_code == 201
    goal_payload = goal_response.json()
    goal_id = goal_payload["id"]
    first_item_id = goal_payload["checklist_items"][0]["id"]

    toggle_response = client.patch(
        f"/api/v1/goals/{goal_id}/checklist-items/{first_item_id}",
        json={"completed": True},
    )
    assert toggle_response.status_code == 200

    dashboard_response = client.post("/api/v1/dashboards", json={"name": "Home"})
    assert dashboard_response.status_code == 201
    dashboard_id = dashboard_response.json()["id"]

    checklist_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "House checklist",
            "widget_type": "goal_checklist",
            "goal_id": goal_id,
        },
    )
    assert checklist_widget_response.status_code == 201
    checklist_widget = checklist_widget_response.json()
    assert checklist_widget["goal"]["goal_type"] == "checklist"
    assert checklist_widget["goal"]["metric"] is None
    assert checklist_widget["goal"]["checklist_completed_count"] == 1
    assert checklist_widget["goal"]["checklist_total_count"] == 2
    assert checklist_widget["current_progress_percent"] == 50.0
    assert checklist_widget["widget_type"] == "goal_checklist"

    progress_widget_response = client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={
            "title": "House progress",
            "widget_type": "goal_progress",
            "goal_id": goal_id,
        },
    )
    assert progress_widget_response.status_code == 201
    progress_widget = progress_widget_response.json()
    assert [point["progress_percent"] for point in progress_widget["series"]] == [0.0, 50.0]
    assert progress_widget["failure_risk_percent"] is not None
