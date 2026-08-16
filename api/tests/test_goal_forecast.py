from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.goal_forecast import ForecastPoint, build_goal_forecast_series


def point(timestamp: str, value: float) -> ForecastPoint:
    return ForecastPoint(timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")), value=value)


def test_builds_simple_slope_forecast_from_first_and_last_actual_points() -> None:
    forecast = build_goal_forecast_series(
        actual_points=[
            point("2026-04-01T00:00:00Z", 250),
            point("2026-04-06T00:00:00Z", 240),
        ],
        algorithm="simple",
        now_timestamp=datetime(2026, 4, 8, tzinfo=UTC),
        target_value=220,
        profile_timezone="UTC",
    )

    assert forecast.bridge_series[-1] == point("2026-04-08T00:00:00Z", 236)
    assert forecast.future_series[-1] == point("2026-04-16T00:00:00Z", 220)


def test_builds_weighted_week_over_week_forecast_from_weekly_changes() -> None:
    now_timestamp = datetime(2026, 4, 22, 12, tzinfo=UTC)
    forecast = build_goal_forecast_series(
        actual_points=[
            point("2026-04-01T12:00:00Z", 250),
            point("2026-04-08T12:00:00Z", 246),
            point("2026-04-15T12:00:00Z", 241),
        ],
        algorithm="weighted_week_over_week",
        now_timestamp=now_timestamp,
        target_value=230,
        profile_timezone="UTC",
    )

    assert forecast.bridge_series[-1].value == pytest.approx(236.44, abs=0.01)
    assert forecast.future_series[-1].timestamp > now_timestamp
    assert forecast.future_series[-1].value == 230


def test_builds_weighted_day_over_day_forecast_using_weekday_deltas() -> None:
    now_timestamp = datetime(2026, 4, 16, 12, tzinfo=UTC)
    forecast = build_goal_forecast_series(
        actual_points=[
            point("2026-04-06T12:00:00Z", 250),
            point("2026-04-07T12:00:00Z", 249),
            point("2026-04-08T12:00:00Z", 247),
            point("2026-04-09T12:00:00Z", 246),
            point("2026-04-13T12:00:00Z", 245),
            point("2026-04-14T12:00:00Z", 244),
            point("2026-04-15T12:00:00Z", 242),
        ],
        algorithm="weighted_day_over_day",
        now_timestamp=now_timestamp,
        target_value=240,
        profile_timezone="America/Chicago",
    )

    assert forecast.bridge_series[-1].value == pytest.approx(240.88, abs=0.01)
    assert forecast.now_point is not None
    assert forecast.now_point.value == pytest.approx(240.88, abs=0.01)
    assert forecast.future_series[-1].timestamp > now_timestamp
    assert forecast.future_series[-1].value == 240


def test_week_over_week_falls_back_to_simple_without_weekly_delta_history() -> None:
    forecast = build_goal_forecast_series(
        actual_points=[
            point("2026-04-01T00:00:00Z", 250),
            point("2026-04-06T00:00:00Z", 240),
        ],
        algorithm="weighted_week_over_week",
        now_timestamp=datetime(2026, 4, 8, tzinfo=UTC),
        target_value=220,
        profile_timezone="UTC",
    )

    assert forecast.bridge_series[-1] == point("2026-04-08T00:00:00Z", 236)
    assert forecast.future_series[-1] == point("2026-04-16T00:00:00Z", 220)


def test_day_over_day_falls_back_to_weekly_without_consecutive_daily_history() -> None:
    forecast = build_goal_forecast_series(
        actual_points=[
            point("2026-04-01T12:00:00Z", 250),
            point("2026-04-08T12:00:00Z", 246),
            point("2026-04-15T12:00:00Z", 241),
        ],
        algorithm="weighted_day_over_day",
        now_timestamp=datetime(2026, 4, 22, 12, tzinfo=UTC),
        target_value=230,
        profile_timezone="UTC",
    )

    assert forecast.bridge_series[-1].value == pytest.approx(236.44, abs=0.01)
    assert forecast.future_series[-1].value == 230
