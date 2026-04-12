from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def seed_dashboard_with_widgets(client: TestClient) -> dict[str, str]:
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
            "number_value": 238.0,
            "recorded_at": "2026-04-05T12:00:00Z",
        },
    )
    assert entry_response.status_code == 200

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
        json={"name": "Weight Dashboard", "description": "Weekly check-in"},
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
    metric_widget_id = metric_widget_response.json()["id"]

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
    goal_widget_id = goal_widget_response.json()["id"]

    return {
        "dashboard_id": dashboard_id,
        "goal_widget_id": goal_widget_id,
        "metric_widget_id": metric_widget_id,
    }


def test_widget_share_links_render_public_og_pages_and_png_previews(client: TestClient) -> None:
    bootstrap_admin(client)
    seeded = seed_dashboard_with_widgets(client)

    before_create = datetime.now(UTC)
    create_response = client.post(
        "/api/v1/share-links",
        json={
            "target_type": "widget",
            "target_id": seeded["goal_widget_id"],
        },
    )
    after_create = datetime.now(UTC)
    assert create_response.status_code == 201

    share_link = create_response.json()
    assert share_link["target_type"] == "widget"
    assert share_link["target_name"] == "Cut Progress"
    assert share_link["dashboard_name"] == "Weight Dashboard"
    assert share_link["widget_type"] == "goal_progress"
    assert share_link["status"] == "active"
    assert share_link["public_path"].startswith("/api/v1/shares/")
    assert share_link["preview_image_path"].endswith("/preview.png")

    expires_at = parse_iso_datetime(share_link["expires_at"])
    assert (
        before_create + timedelta(days=29, hours=23)
        <= expires_at
        <= (after_create + timedelta(days=30, minutes=1))
    )

    inventory_response = client.get("/api/v1/share-links")
    assert inventory_response.status_code == 200
    assert inventory_response.json()["share_links"][0]["id"] == share_link["id"]

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    cache_bust = "1760000000"
    page_response = client.get(f"{share_link['public_path']}?t={cache_bust}")
    assert page_response.status_code == 200
    assert page_response.headers["content-type"].startswith("text/html")
    assert page_response.headers["cache-control"] == "no-cache, no-store, must-revalidate"
    assert page_response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "Cut Progress" in page_response.text
    assert f"http://testserver{share_link['preview_image_path']}?t={cache_bust}" in page_response.text
    assert '<meta property="og:title" content="Cut Progress - ' in page_response.text
    assert 'property="og:description"' not in page_response.text
    assert 'twitter:card" content="summary_large_image"' in page_response.text
    assert 'class="widget-chart"' in page_response.text
    assert "/vendor/echarts.min.js" in page_response.text
    assert "Widget graph" in page_response.text
    assert 'class="preview-image"' not in page_response.text
    assert "Edit dashboard" not in page_response.text

    preview_response = client.get(share_link["preview_image_path"])
    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "image/png"
    assert preview_response.headers["cache-control"] == "no-cache, no-store, must-revalidate"
    assert preview_response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_dashboard_share_links_support_unlimited_expiration_and_read_only_dashboard_view(
    client: TestClient,
) -> None:
    bootstrap_admin(client)
    seeded = seed_dashboard_with_widgets(client)

    create_response = client.post(
        "/api/v1/share-links",
        json={
            "target_type": "dashboard",
            "target_id": seeded["dashboard_id"],
            "expires_in_days": None,
        },
    )
    assert create_response.status_code == 201

    share_link = create_response.json()
    assert share_link["target_type"] == "dashboard"
    assert share_link["target_name"] == "Weight Dashboard"
    assert share_link["dashboard_name"] == "Weight Dashboard"
    assert share_link["widget_type"] is None
    assert share_link["expires_at"] is None
    assert share_link["status"] == "active"

    page_response = client.get(share_link["public_path"])
    assert page_response.status_code == 200
    assert "Weight Dashboard" in page_response.text
    assert "Weight Trend" in page_response.text
    assert "Cut Progress" in page_response.text
    assert "Read-only dashboard share." not in page_response.text
    assert "Edit dashboard" not in page_response.text


def test_share_links_include_the_configured_app_base_path(prefixed_client: TestClient) -> None:
    bootstrap_admin(prefixed_client)
    seeded = seed_dashboard_with_widgets(prefixed_client)

    create_response = prefixed_client.post(
        "/api/v1/share-links",
        json={
            "target_type": "widget",
            "target_id": seeded["goal_widget_id"],
        },
    )
    assert create_response.status_code == 201

    share_link = create_response.json()
    assert share_link["public_path"].startswith("/goals/api/v1/shares/")
    assert share_link["preview_image_path"].startswith("/goals/api/v1/shares/")

    logout_response = prefixed_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    page_response = prefixed_client.get(share_link["public_path"].removeprefix("/goals"))
    assert page_response.status_code == 200
    assert "/goals/vendor/echarts.min.js" in page_response.text


def test_revoking_share_links_blocks_public_access_and_updates_status(client: TestClient) -> None:
    bootstrap_admin(client)
    seeded = seed_dashboard_with_widgets(client)

    create_response = client.post(
        "/api/v1/share-links",
        json={
            "target_type": "widget",
            "target_id": seeded["metric_widget_id"],
        },
    )
    assert create_response.status_code == 201
    share_link = create_response.json()

    revoke_response = client.delete(f"/api/v1/share-links/{share_link['id']}")
    assert revoke_response.status_code == 204

    inventory_response = client.get("/api/v1/share-links")
    assert inventory_response.status_code == 200
    assert inventory_response.json()["share_links"][0]["status"] == "revoked"
    assert inventory_response.json()["share_links"][0]["revoked_at"] is not None

    page_response = client.get(share_link["public_path"])
    assert page_response.status_code == 404

    preview_response = client.get(share_link["preview_image_path"])
    assert preview_response.status_code == 404
