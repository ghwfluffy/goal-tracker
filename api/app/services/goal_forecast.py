from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_FORECAST_DAYS = 3650


@dataclass(frozen=True)
class ForecastPoint:
    timestamp: datetime
    value: float


@dataclass(frozen=True)
class ForecastSeries:
    bridge_series: list[ForecastPoint]
    future_series: list[ForecastPoint]
    now_point: ForecastPoint | None


@dataclass(frozen=True)
class _DailyPoint:
    average_value: float
    day_index: int
    day_of_week: int


def _empty_forecast_series() -> ForecastSeries:
    return ForecastSeries(bridge_series=[], future_series=[], now_point=None)


def _safe_zoneinfo(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")


def _local_day_start(timestamp: datetime, timezone: ZoneInfo) -> datetime:
    local_date = timestamp.astimezone(timezone).date()
    return datetime.combine(local_date, time.min, tzinfo=timezone).astimezone(UTC)


def _next_local_day_start(timestamp: datetime, timezone: ZoneInfo) -> datetime:
    local_date = timestamp.astimezone(timezone).date() + timedelta(days=1)
    return datetime.combine(local_date, time.min, tzinfo=timezone).astimezone(UTC)


def _build_daily_points(
    points: list[ForecastPoint],
    *,
    now_timestamp: datetime,
    timezone: ZoneInfo,
) -> list[_DailyPoint]:
    buckets: dict[int, tuple[int, int, float]] = {}
    for point in points:
        if not math.isfinite(point.value) or point.timestamp > now_timestamp:
            continue

        local_date = point.timestamp.astimezone(timezone).date()
        day_index = local_date.toordinal()
        day_of_week = (local_date.weekday() + 1) % 7
        count, stored_day_of_week, value_sum = buckets.get(day_index, (0, day_of_week, 0.0))
        buckets[day_index] = (count + 1, stored_day_of_week, value_sum + point.value)

    return [
        _DailyPoint(
            average_value=value_sum / count,
            day_index=day_index,
            day_of_week=day_of_week,
        )
        for day_index, (count, day_of_week, value_sum) in sorted(buckets.items())
    ]


def _weighted_average(values: list[float]) -> float | None:
    if len(values) == 0:
        return None
    if len(values) == 1:
        return values[0]

    maximum_index = len(values) - 1
    weighted_sum = 0.0
    weight_total = 0.0
    for index, value in enumerate(values):
        weight = 0.8 + (0.2 * index) / maximum_index
        weighted_sum += value * weight
        weight_total += weight
    return weighted_sum / weight_total if weight_total > 0 else None


def _build_linear_forecast_series(
    *,
    last_actual_point: ForecastPoint,
    now_timestamp: datetime,
    slope_per_second: float | None,
    target_value: float,
) -> ForecastSeries:
    if slope_per_second is None or not math.isfinite(slope_per_second) or slope_per_second == 0:
        return _empty_forecast_series()

    bridge_series: list[ForecastPoint] = []
    now_point: ForecastPoint | None = None
    if now_timestamp > last_actual_point.timestamp:
        now_point = ForecastPoint(
            timestamp=now_timestamp,
            value=(
                last_actual_point.value
                + slope_per_second * (now_timestamp - last_actual_point.timestamp).total_seconds()
            ),
        )
        bridge_series = [last_actual_point, now_point]

    target_offset_seconds = (target_value - last_actual_point.value) / slope_per_second
    projected_target_timestamp: datetime | None = None
    if target_offset_seconds > 0 and math.isfinite(target_offset_seconds):
        try:
            projected_target_timestamp = last_actual_point.timestamp + timedelta(
                seconds=target_offset_seconds
            )
        except OverflowError:
            projected_target_timestamp = None

    future_series: list[ForecastPoint] = []
    if projected_target_timestamp is not None and projected_target_timestamp > last_actual_point.timestamp:
        future_start = now_point or last_actual_point
        if projected_target_timestamp > future_start.timestamp:
            future_series = [
                future_start,
                ForecastPoint(timestamp=projected_target_timestamp, value=target_value),
            ]

    return ForecastSeries(
        bridge_series=bridge_series,
        future_series=future_series,
        now_point=now_point,
    )


def _build_weighted_day_over_day_deltas(
    points: list[ForecastPoint],
    *,
    now_timestamp: datetime,
    timezone: ZoneInfo,
) -> tuple[float | None, list[float | None]]:
    daily_points = _build_daily_points(points, now_timestamp=now_timestamp, timezone=timezone)
    weekday_diffs: list[list[float]] = [[] for _ in range(7)]
    all_diffs: list[float] = []

    for previous_point, current_point in zip(daily_points, daily_points[1:], strict=False):
        if current_point.day_index != previous_point.day_index + 1:
            continue
        delta = current_point.average_value - previous_point.average_value
        weekday_diffs[previous_point.day_of_week].append(delta)
        all_diffs.append(delta)

    return _weighted_average(all_diffs), [_weighted_average(deltas) for deltas in weekday_diffs]


def _advance_weighted_day_over_day(
    *,
    limit_timestamp: datetime,
    overall_delta: float | None,
    start_state: ForecastPoint,
    target_value: float | None,
    timezone: ZoneInfo,
    weekday_deltas: list[float | None],
) -> tuple[list[ForecastPoint], ForecastPoint | None]:
    points = [start_state]
    cursor = start_state

    for _ in range(MAX_FORECAST_DAYS):
        if cursor.timestamp >= limit_timestamp:
            break

        local_date = cursor.timestamp.astimezone(timezone).date()
        day_of_week = (local_date.weekday() + 1) % 7
        full_day_delta = weekday_deltas[day_of_week]
        if full_day_delta is None:
            full_day_delta = overall_delta
        if full_day_delta is None or not math.isfinite(full_day_delta):
            break

        current_day_start = _local_day_start(cursor.timestamp, timezone)
        next_day_start = _next_local_day_start(cursor.timestamp, timezone)
        segment_end_timestamp = min(next_day_start, limit_timestamp)
        full_day_duration = (next_day_start - current_day_start).total_seconds()
        segment_duration = (segment_end_timestamp - cursor.timestamp).total_seconds()
        if full_day_duration <= 0 or segment_duration <= 0:
            break

        segment_delta = full_day_delta * (segment_duration / full_day_duration)
        next_value = cursor.value + segment_delta
        target_is_in_segment = (
            target_value is not None
            and segment_delta != 0
            and (
                (segment_delta > 0 and cursor.value <= target_value <= next_value)
                or (segment_delta < 0 and next_value <= target_value <= cursor.value)
            )
        )
        if target_is_in_segment and target_value is not None:
            fraction = (target_value - cursor.value) / segment_delta
            target_point = ForecastPoint(
                timestamp=cursor.timestamp + timedelta(seconds=segment_duration * fraction),
                value=target_value,
            )
            points.append(target_point)
            return points, target_point

        cursor = ForecastPoint(timestamp=segment_end_timestamp, value=next_value)
        points.append(cursor)

    return points, None


def _build_weighted_day_over_day_series(
    actual_points: list[ForecastPoint],
    *,
    last_actual_point: ForecastPoint,
    now_timestamp: datetime,
    target_value: float,
    timezone: ZoneInfo,
) -> ForecastSeries:
    overall_delta, weekday_deltas = _build_weighted_day_over_day_deltas(
        actual_points,
        now_timestamp=now_timestamp,
        timezone=timezone,
    )
    if overall_delta is None or not math.isfinite(overall_delta):
        return _empty_forecast_series()

    if now_timestamp > last_actual_point.timestamp:
        bridge_projection, _ = _advance_weighted_day_over_day(
            limit_timestamp=now_timestamp,
            overall_delta=overall_delta,
            start_state=last_actual_point,
            target_value=None,
            timezone=timezone,
            weekday_deltas=weekday_deltas,
        )
    else:
        bridge_projection = [last_actual_point]

    bridge_series = bridge_projection if len(bridge_projection) > 1 else []
    now_point = bridge_projection[-1] if now_timestamp > last_actual_point.timestamp else None
    future_start = now_point or last_actual_point
    future_projection, reached_target = _advance_weighted_day_over_day(
        limit_timestamp=future_start.timestamp + timedelta(days=MAX_FORECAST_DAYS),
        overall_delta=overall_delta,
        start_state=future_start,
        target_value=target_value,
        timezone=timezone,
        weekday_deltas=weekday_deltas,
    )

    return ForecastSeries(
        bridge_series=bridge_series,
        future_series=future_projection if reached_target is not None else [],
        now_point=now_point,
    )


def _build_simple_series(
    actual_points: list[ForecastPoint],
    *,
    now_timestamp: datetime,
    target_value: float,
) -> ForecastSeries:
    if len(actual_points) < 2:
        return _empty_forecast_series()
    first_actual_point = actual_points[0]
    last_actual_point = actual_points[-1]
    duration = (last_actual_point.timestamp - first_actual_point.timestamp).total_seconds()
    if duration <= 0:
        return _empty_forecast_series()
    return _build_linear_forecast_series(
        last_actual_point=last_actual_point,
        now_timestamp=now_timestamp,
        slope_per_second=(last_actual_point.value - first_actual_point.value) / duration,
        target_value=target_value,
    )


def _build_weighted_week_over_week_series(
    actual_points: list[ForecastPoint],
    *,
    now_timestamp: datetime,
    target_value: float,
    timezone: ZoneInfo,
) -> ForecastSeries:
    if len(actual_points) == 0:
        return _empty_forecast_series()
    last_actual_point = actual_points[-1]
    daily_points = _build_daily_points(
        actual_points,
        now_timestamp=now_timestamp,
        timezone=timezone,
    )
    if len(daily_points) < 2:
        return _empty_forecast_series()

    first_day_index = daily_points[0].day_index
    weekly_buckets: dict[int, tuple[int, float]] = {}
    for point in daily_points:
        week_index = (point.day_index - first_day_index) // 7
        count, value_sum = weekly_buckets.get(week_index, (0, 0.0))
        weekly_buckets[week_index] = (count + 1, value_sum + point.average_value)

    weekly_averages = [
        (week_index, value_sum / count) for week_index, (count, value_sum) in sorted(weekly_buckets.items())
    ]
    weekly_diffs = [
        current_average - previous_average
        for (previous_week, previous_average), (current_week, current_average) in zip(
            weekly_averages,
            weekly_averages[1:],
            strict=False,
        )
        if current_week == previous_week + 1
    ]
    weekly_delta = _weighted_average(weekly_diffs)
    slope_per_second = (
        None if weekly_delta is None or not math.isfinite(weekly_delta) else weekly_delta / (7 * 86400)
    )
    return _build_linear_forecast_series(
        last_actual_point=last_actual_point,
        now_timestamp=now_timestamp,
        slope_per_second=slope_per_second,
        target_value=target_value,
    )


def build_goal_forecast_series(
    *,
    actual_points: list[ForecastPoint],
    algorithm: str,
    now_timestamp: datetime,
    target_value: float,
    profile_timezone: str,
) -> ForecastSeries:
    if len(actual_points) == 0:
        return _empty_forecast_series()

    timezone = _safe_zoneinfo(profile_timezone)
    last_actual_point = actual_points[-1]
    if algorithm == "weighted_day_over_day":
        day_series = _build_weighted_day_over_day_series(
            actual_points,
            last_actual_point=last_actual_point,
            now_timestamp=now_timestamp,
            target_value=target_value,
            timezone=timezone,
        )
        if len(day_series.future_series) > 0:
            return day_series
        week_series = _build_weighted_week_over_week_series(
            actual_points,
            now_timestamp=now_timestamp,
            target_value=target_value,
            timezone=timezone,
        )
        if len(week_series.future_series) > 0:
            return week_series
        return _build_simple_series(
            actual_points,
            now_timestamp=now_timestamp,
            target_value=target_value,
        )

    if algorithm == "weighted_week_over_week":
        week_series = _build_weighted_week_over_week_series(
            actual_points,
            now_timestamp=now_timestamp,
            target_value=target_value,
            timezone=timezone,
        )
        if len(week_series.future_series) > 0:
            return week_series

    return _build_simple_series(
        actual_points,
        now_timestamp=now_timestamp,
        target_value=target_value,
    )
