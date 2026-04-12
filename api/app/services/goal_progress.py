from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db.models import Goal, MetricEntry, User
from app.services.metrics import METRIC_TYPE_DATE, METRIC_TYPE_NUMBER


@dataclass
class GoalDateProgressPoint:
    recorded_at: datetime
    progress_percent: float


@dataclass
class GoalProgressPoint:
    recorded_at: datetime
    number_value: float | int | None
    date_value: date | None
    progress_percent: float


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_recorded_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_user_timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")


def goal_entry_effective_date(entry: MetricEntry) -> date:
    if entry.date_value is not None:
        return entry.date_value
    return normalize_recorded_at(entry.recorded_at).date()


def goal_exception_date_values(goal: Goal) -> set[date]:
    return {exception_date.exception_date for exception_date in goal.exception_dates}


def goal_start_datetime(goal: Goal) -> datetime:
    user_timezone = get_user_timezone(goal.user)
    return datetime.combine(goal.start_date, time.min, tzinfo=user_timezone).astimezone(UTC)


def goal_end_datetime(goal: Goal) -> datetime | None:
    if goal.target_date is None:
        return None

    user_timezone = get_user_timezone(goal.user)
    return datetime.combine(
        goal.target_date + timedelta(days=1),
        time.min,
        tzinfo=user_timezone,
    ).astimezone(UTC)


def sort_metric_entries_ascending(entries: list[MetricEntry]) -> list[MetricEntry]:
    return sorted(entries, key=lambda entry: normalize_recorded_at(entry.recorded_at))


def metric_entry_numeric_value(goal: Goal, entry: MetricEntry) -> float | int | None:
    if goal.metric.metric_type == METRIC_TYPE_NUMBER:
        return entry.number_value
    if entry.date_value is None:
        return None
    return entry.date_value.toordinal()


def goal_target_numeric_value(goal: Goal) -> float | int | None:
    if goal.metric.metric_type == METRIC_TYPE_NUMBER:
        return goal.target_value_number
    if goal.target_value_date is None:
        return None
    return goal.target_value_date.toordinal()


def find_goal_baseline_entry(goal: Goal, ordered_entries: list[MetricEntry]) -> MetricEntry | None:
    start_cutoff = goal_start_datetime(goal)
    baseline_entry: MetricEntry | None = None
    first_after_start: MetricEntry | None = None

    for entry in ordered_entries:
        recorded_at = normalize_recorded_at(entry.recorded_at)
        if recorded_at <= start_cutoff:
            baseline_entry = entry
            continue
        if first_after_start is None:
            first_after_start = entry
            break

    return baseline_entry or first_after_start


def calculate_progress_percent(
    *,
    baseline_value: float | int,
    target_value: float | int,
    current_value: float | int,
) -> float:
    if target_value == baseline_value:
        return 100.0 if current_value == target_value else 0.0

    progress_ratio = (float(current_value) - float(baseline_value)) / (
        float(target_value) - float(baseline_value)
    )
    return round(max(0.0, min(progress_ratio * 100.0, 100.0)), 2)


def is_target_met(
    *, baseline_value: float | int, target_value: float | int, current_value: float | int
) -> bool:
    if target_value == baseline_value:
        return current_value == target_value
    if target_value > baseline_value:
        return current_value >= target_value
    return current_value <= target_value


def goal_progress_as_of_date(goal: Goal, *, as_of_date: date | None = None) -> float | None:
    if goal.metric.metric_type != METRIC_TYPE_DATE:
        return None
    if goal.target_date is None:
        return None

    comparison_date = as_of_date or utcnow().astimezone(get_user_timezone(goal.user)).date()
    effective_end = min(goal.target_date, comparison_date)
    if effective_end < goal.start_date:
        return None

    exception_dates = goal_exception_date_values(goal)
    eligible_days = 0
    successful_days = 0
    violation_dates = {
        goal_entry_effective_date(entry)
        for entry in goal.metric.entries
        if goal.start_date <= goal_entry_effective_date(entry) <= effective_end
    }

    current_day = goal.start_date
    while current_day <= effective_end:
        if current_day not in exception_dates:
            eligible_days += 1
            if current_day not in violation_dates:
                successful_days += 1
        current_day += timedelta(days=1)

    if eligible_days == 0:
        return None
    return round((successful_days / eligible_days) * 100, 2)


def goal_current_progress_percent(goal: Goal) -> float | None:
    if goal.metric.metric_type == METRIC_TYPE_DATE:
        return goal_progress_as_of_date(goal)

    target_value = goal_target_numeric_value(goal)
    if target_value is None:
        return None

    ordered_entries = sort_metric_entries_ascending(goal.metric.entries)
    if len(ordered_entries) == 0:
        return None

    baseline_entry = find_goal_baseline_entry(goal, ordered_entries)
    if baseline_entry is None:
        return None

    baseline_value = metric_entry_numeric_value(goal, baseline_entry)
    if baseline_value is None:
        return None

    start_cutoff = goal_start_datetime(goal)
    current_entry = baseline_entry
    for entry in ordered_entries:
        if normalize_recorded_at(entry.recorded_at) >= start_cutoff:
            current_entry = entry

    current_value = metric_entry_numeric_value(goal, current_entry)
    if current_value is None:
        return None

    return calculate_progress_percent(
        baseline_value=baseline_value,
        target_value=target_value,
        current_value=current_value,
    )


def goal_target_met(goal: Goal) -> bool | None:
    if goal.metric.metric_type == METRIC_TYPE_DATE:
        current_progress = goal_progress_as_of_date(goal)
        if current_progress is None or goal.success_threshold_percent is None:
            return None
        return current_progress >= float(goal.success_threshold_percent)

    target_value = goal_target_numeric_value(goal)
    if target_value is None:
        return None

    ordered_entries = sort_metric_entries_ascending(goal.metric.entries)
    if len(ordered_entries) == 0:
        return None

    baseline_entry = find_goal_baseline_entry(goal, ordered_entries)
    if baseline_entry is None:
        return None

    baseline_value = metric_entry_numeric_value(goal, baseline_entry)
    if baseline_value is None:
        return None

    start_cutoff = goal_start_datetime(goal)
    current_entry = baseline_entry
    for entry in ordered_entries:
        if normalize_recorded_at(entry.recorded_at) >= start_cutoff:
            current_entry = entry

    current_value = metric_entry_numeric_value(goal, current_entry)
    if current_value is None:
        return None

    return is_target_met(
        baseline_value=baseline_value,
        target_value=target_value,
        current_value=current_value,
    )


def goal_time_completion_percent(goal: Goal, *, as_of: datetime | None = None) -> float | None:
    end_datetime = goal_end_datetime(goal)
    if end_datetime is None:
        return None

    start_datetime = goal_start_datetime(goal)
    comparison_datetime = normalize_recorded_at(as_of or utcnow())
    if comparison_datetime <= start_datetime:
        return 0.0
    if comparison_datetime >= end_datetime:
        return 100.0

    total_seconds = (end_datetime - start_datetime).total_seconds()
    if total_seconds <= 0:
        return 100.0

    elapsed_seconds = (comparison_datetime - start_datetime).total_seconds()
    return round(max(0.0, min((elapsed_seconds / total_seconds) * 100.0, 100.0)), 2)


def goal_failure_risk_percent(goal: Goal) -> float | None:
    success_percent = goal_current_progress_percent(goal)
    time_completion_percent = goal_time_completion_percent(goal)
    if success_percent is None or time_completion_percent is None:
        return None
    return round(max(0.0, time_completion_percent - success_percent), 2)


def build_goal_date_progress_points(goal: Goal) -> list[GoalDateProgressPoint]:
    if goal.metric.metric_type != METRIC_TYPE_DATE or goal.target_date is None:
        return []

    today = utcnow().astimezone(get_user_timezone(goal.user)).date()
    effective_end = min(goal.target_date, today)
    if effective_end < goal.start_date:
        return []

    points: list[GoalDateProgressPoint] = []
    current_day = goal.start_date
    while current_day <= effective_end:
        progress_percent = goal_progress_as_of_date(goal, as_of_date=current_day)
        if progress_percent is not None:
            points.append(
                GoalDateProgressPoint(
                    recorded_at=datetime.combine(current_day, time(hour=12), tzinfo=UTC),
                    progress_percent=progress_percent,
                )
            )
        current_day += timedelta(days=1)
    return points


def build_goal_progress_points(goal: Goal, *, rolling_window_days: int | None) -> list[GoalProgressPoint]:
    effective_window = None if goal.target_date is not None else rolling_window_days

    if goal.metric.metric_type == METRIC_TYPE_DATE:
        date_points = build_goal_date_progress_points(goal)
        if effective_window is not None:
            window_threshold = utcnow() - timedelta(days=effective_window)
            date_points = [
                point for point in date_points if normalize_recorded_at(point.recorded_at) >= window_threshold
            ]
        return [
            GoalProgressPoint(
                recorded_at=point.recorded_at,
                number_value=None,
                date_value=None,
                progress_percent=point.progress_percent,
            )
            for point in date_points
        ]

    target_value = goal_target_numeric_value(goal)
    if target_value is None:
        return []

    ordered_entries = sort_metric_entries_ascending(goal.metric.entries)
    if len(ordered_entries) == 0:
        return []

    baseline_entry = find_goal_baseline_entry(goal, ordered_entries)
    if baseline_entry is None:
        return []

    baseline_value = metric_entry_numeric_value(goal, baseline_entry)
    if baseline_value is None:
        return []

    start_cutoff = goal_start_datetime(goal)
    numeric_window_threshold: datetime | None = (
        utcnow() - timedelta(days=effective_window) if effective_window is not None else None
    )

    points: list[GoalProgressPoint] = [
        GoalProgressPoint(
            recorded_at=start_cutoff,
            number_value=baseline_entry.number_value,
            date_value=baseline_entry.date_value,
            progress_percent=0.0,
        )
    ]
    for entry in ordered_entries:
        recorded_at = normalize_recorded_at(entry.recorded_at)
        if recorded_at < start_cutoff:
            continue
        if numeric_window_threshold is not None and recorded_at < numeric_window_threshold:
            continue

        current_value = metric_entry_numeric_value(goal, entry)
        if current_value is None:
            continue
        if current_value == baseline_value and len(points) == 1:
            continue

        points.append(
            GoalProgressPoint(
                recorded_at=entry.recorded_at,
                number_value=entry.number_value,
                date_value=entry.date_value,
                progress_percent=calculate_progress_percent(
                    baseline_value=baseline_value,
                    target_value=target_value,
                    current_value=current_value,
                ),
            )
        )

    return points
