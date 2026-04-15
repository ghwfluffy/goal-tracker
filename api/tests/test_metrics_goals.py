from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
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
    assert payload["update_type"] == "success"
    assert payload["latest_entry"]["date_value"] == "2026-04-10"


def test_create_date_metric_with_failure_update_type(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last drink",
            "metric_type": "date",
            "update_type": "failure",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["metric_type"] == "date"
    assert payload["update_type"] == "failure"


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


def test_metric_schedule_fields_can_be_created_and_updated(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "reminder_time_1": "06:00",
            "reminder_time_2": "16:30",
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["reminder_time_1"] == "06:00"
    assert payload["reminder_time_2"] == "16:30"

    update_response = client.patch(
        f"/api/v1/metrics/{payload['id']}",
        json={
            "name": "Morning Weight",
            "reminder_time_1": "07:15",
            "reminder_time_2": None,
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["name"] == "Morning Weight"
    assert updated_payload["reminder_time_1"] == "07:15"
    assert updated_payload["reminder_time_2"] is None


def test_import_number_metric_entries_is_idempotent(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "unit_label": "lbs",
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    import_response = client.post(
        f"/api/v1/metrics/{metric_id}/import",
        json={
            "data": "recorded_at\tvalue\n2026-01-05 20:56\t298.6\n2026-01-06 07:00\t296.6\n",
        },
    )

    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0
    assert len(payload["metric"]["entries"]) == 2
    assert payload["metric"]["entries"][0]["number_value"] == 296.6
    assert payload["metric"]["entries"][0]["recorded_at"] == "2026-01-06T13:00:00"
    assert payload["metric"]["entries"][1]["recorded_at"] == "2026-01-06T02:56:00"

    repeat_response = client.post(
        f"/api/v1/metrics/{metric_id}/import",
        json={
            "data": "2026-01-05 20:56,298.6\n2026-01-06 07:00,296.6\n",
        },
    )
    assert repeat_response.status_code == 200
    repeat_payload = repeat_response.json()
    assert repeat_payload["imported_count"] == 0
    assert repeat_payload["skipped_count"] == 2
    assert len(repeat_payload["metric"]["entries"]) == 2


def test_import_rejects_conflicting_existing_metric_entry(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    update_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={
            "number_value": 245.5,
            "recorded_at": "2026-01-06T02:56:00Z",
        },
    )
    assert update_response.status_code == 200

    import_response = client.post(
        f"/api/v1/metrics/{metric_id}/import",
        json={
            "data": "2026-01-05 20:56\t244.5\n",
        },
    )
    assert import_response.status_code == 422
    assert (
        import_response.json()["detail"]
        == "Import line 1 conflicts with an existing entry at 2026-01-06T02:56:00+00:00."
    )


def test_due_number_metric_notification_can_be_completed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap_admin(client)
    scheduled_at = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(minutes=1)
    created_at = scheduled_at - timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.metrics.utcnow",
        lambda: created_at,
    )

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "reminder_time_1": scheduled_at.strftime("%H:%M"),
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    monkeypatch.setattr(
        "app.services.notifications.utcnow",
        lambda: scheduled_at,
    )

    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    assert "goal_tracker_session=" in notification_list_response.headers["set-cookie"]
    notifications = notification_list_response.json()["notifications"]
    assert len(notifications) == 1
    notification_id = notifications[0]["id"]
    assert notifications[0]["metric"]["id"] == metric_id

    complete_response = client.post(
        f"/api/v1/notifications/{notification_id}/complete",
        json={
            "number_value": 244.4,
            "recorded_at": scheduled_at.isoformat().replace("+00:00", "Z"),
            "timezone": "UTC",
        },
    )
    assert complete_response.status_code == 200

    metric_response = client.get("/api/v1/metrics")
    assert metric_response.status_code == 200
    assert metric_response.json()["metrics"][0]["latest_entry"]["number_value"] == 244.4

    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    assert notification_list_response.json() == {"notifications": []}


def test_manual_metric_entry_clears_matching_pending_notification(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap_admin(client)
    scheduled_at = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(minutes=1)
    created_at = scheduled_at - timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.metrics.utcnow",
        lambda: created_at,
    )

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Weight",
            "metric_type": "number",
            "decimal_places": 1,
            "reminder_time_1": scheduled_at.strftime("%H:%M"),
        },
    )
    assert create_response.status_code == 201
    metric_id = create_response.json()["id"]

    monkeypatch.setattr(
        "app.services.notifications.utcnow",
        lambda: scheduled_at,
    )
    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    assert len(notification_list_response.json()["notifications"]) == 1

    entry_response = client.post(
        f"/api/v1/metrics/{metric_id}/entries",
        json={
            "number_value": 244.4,
            "recorded_at": scheduled_at.isoformat().replace("+00:00", "Z"),
        },
    )
    assert entry_response.status_code == 200

    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    assert notification_list_response.json() == {"notifications": []}


def test_due_date_metric_notification_can_be_skipped(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap_admin(client)
    scheduled_at = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(minutes=1)
    created_at = scheduled_at - timedelta(minutes=1)

    monkeypatch.setattr(
        "app.services.metrics.utcnow",
        lambda: created_at,
    )

    create_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Cardio Date",
            "metric_type": "date",
            "reminder_time_1": scheduled_at.strftime("%H:%M"),
        },
    )
    assert create_response.status_code == 201

    monkeypatch.setattr(
        "app.services.notifications.utcnow",
        lambda: scheduled_at,
    )

    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    notification_id = notification_list_response.json()["notifications"][0]["id"]

    skip_response = client.post(f"/api/v1/notifications/{notification_id}/skip")
    assert skip_response.status_code == 200

    notification_list_response = client.get("/api/v1/notifications?timezone=UTC")
    assert notification_list_response.status_code == 200
    assert notification_list_response.json() == {"notifications": []}


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


def test_archived_goals_are_hidden_by_default_and_can_be_included(client: TestClient) -> None:
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
            "start_date": "2026-04-11",
            "target_date": "2026-06-30",
            "target_value_number": 220.0,
            "metric_id": metric_response.json()["id"],
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    archive_response = client.patch(f"/api/v1/goals/{goal_id}", json={"archived": True})
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True

    default_list_response = client.get("/api/v1/goals")
    assert default_list_response.status_code == 200
    assert default_list_response.json() == {"goals": []}

    archived_list_response = client.get("/api/v1/goals?include_archived=true")
    assert archived_list_response.status_code == 200
    assert len(archived_list_response.json()["goals"]) == 1
    assert archived_list_response.json()["goals"][0]["is_archived"] is True


def test_goal_details_can_be_updated_after_creation(client: TestClient) -> None:
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
    goal_id = goal_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/goals/{goal_id}",
        json={
            "title": "Reach 215",
            "description": "Updated target after a stronger start.",
            "target_date": "2026-06-15",
            "target_value_number": 215.0,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["title"] == "Reach 215"
    assert payload["description"] == "Updated target after a stronger start."
    assert payload["target_date"] == "2026-06-15"
    assert payload["target_value_number"] == 215.0


def test_date_goal_updates_replace_exception_dates(client: TestClient) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last Drink",
            "metric_type": "date",
            "initial_date_value": "2026-04-10",
        },
    )
    assert metric_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinks",
            "start_date": "2026-04-11",
            "target_date": "2026-04-30",
            "success_threshold_percent": 100,
            "exception_dates": ["2026-04-20"],
            "metric_id": metric_response.json()["id"],
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/goals/{goal_id}",
        json={
            "description": "Allow one planned exception.",
            "success_threshold_percent": 80,
            "exception_dates": ["2026-04-18", "2026-04-22"],
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["description"] == "Allow one planned exception."
    assert payload["success_threshold_percent"] == 80.0
    assert payload["exception_dates"] == ["2026-04-18", "2026-04-22"]


def test_date_goal_updates_preserve_existing_exception_dates_when_adding_more(
    client: TestClient,
) -> None:
    bootstrap_admin(client)

    metric_response = client.post(
        "/api/v1/metrics",
        json={
            "name": "Last Drink",
            "metric_type": "date",
            "initial_date_value": "2026-04-10",
        },
    )
    assert metric_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "No drinks",
            "start_date": "2026-04-11",
            "target_date": "2026-04-30",
            "success_threshold_percent": 100,
            "exception_dates": ["2026-04-17"],
            "metric_id": metric_response.json()["id"],
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/goals/{goal_id}",
        json={
            "exception_dates": ["2026-04-17", "2026-04-24", "2026-04-28", "2026-04-30"],
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["exception_dates"] == [
        "2026-04-17",
        "2026-04-24",
        "2026-04-28",
        "2026-04-30",
    ]


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


def test_checklist_goal_can_be_created_and_items_toggled(client: TestClient) -> None:
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
    payload = goal_response.json()
    assert payload["goal_type"] == "checklist"
    assert payload["metric"] is None
    assert payload["checklist_total_count"] == 2
    assert payload["checklist_completed_count"] == 0
    assert payload["current_progress_percent"] == 0.0
    assert payload["target_met"] is False

    first_item_id = payload["checklist_items"][0]["id"]
    toggle_response = client.patch(
        f"/api/v1/goals/{payload['id']}/checklist-items/{first_item_id}",
        json={"completed": True},
    )
    assert toggle_response.status_code == 200
    toggled_payload = toggle_response.json()
    assert toggled_payload["checklist_completed_count"] == 1
    assert toggled_payload["current_progress_percent"] == 50.0
    assert toggled_payload["checklist_items"][0]["is_completed"] is True
    assert toggled_payload["failure_risk_percent"] is not None

    clear_response = client.patch(
        f"/api/v1/goals/{payload['id']}/checklist-items/{first_item_id}",
        json={"completed": False},
    )
    assert clear_response.status_code == 200
    cleared_payload = clear_response.json()
    assert cleared_payload["checklist_completed_count"] == 0
    assert cleared_payload["current_progress_percent"] == 0.0
    assert cleared_payload["checklist_items"][0]["is_completed"] is False


def test_checklist_goal_updates_preserve_completed_items_by_id(client: TestClient) -> None:
    bootstrap_admin(client)

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "goal_type": "checklist",
            "title": "Weekend reset",
            "start_date": "2026-04-11",
            "checklist_items": [
                {"title": "Wash dishes"},
                {"title": "Fold clothes"},
            ],
        },
    )
    assert goal_response.status_code == 201
    payload = goal_response.json()
    first_item_id = payload["checklist_items"][0]["id"]

    toggle_response = client.patch(
        f"/api/v1/goals/{payload['id']}/checklist-items/{first_item_id}",
        json={"completed": True},
    )
    assert toggle_response.status_code == 200

    update_response = client.patch(
        f"/api/v1/goals/{payload['id']}",
        json={
            "checklist_items": [
                {"id": first_item_id, "title": "Wash dishes and sink"},
                {"title": "Vacuum rug"},
            ],
            "target_date": "2026-04-14",
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert [item["title"] for item in updated_payload["checklist_items"]] == [
        "Wash dishes and sink",
        "Vacuum rug",
    ]
    assert updated_payload["checklist_items"][0]["is_completed"] is True
    assert updated_payload["current_progress_percent"] == 50.0
    assert updated_payload["target_date"] == "2026-04-14"


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

    notifications_response = client.get("/api/v1/notifications?timezone=America/Chicago")
    assert notifications_response.status_code == 200
    assert len(notifications_response.json()["notifications"]) == 4
