from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Goal, GoalExceptionDate, Metric, MetricEntry, User
from app.services.metrics import METRIC_TYPE_DATE, METRIC_TYPE_NUMBER


class GoalError(Exception):
    pass


class GoalNotFoundError(Exception):
    pass


def list_goals_for_user(db: Session, user: User) -> list[Goal]:
    statement = (
        select(Goal)
        .options(
            selectinload(Goal.metric).selectinload(Metric.entries),
            selectinload(Goal.exception_dates),
        )
        .where(Goal.user_id == user.id)
        .order_by(Goal.created_at.desc())
    )
    return list(db.scalars(statement))


def normalize_success_threshold_percent(value: float | None) -> Decimal | None:
    if value is None:
        return None
    normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if normalized < 0 or normalized > 100:
        raise GoalError("Success threshold percent must be between 0 and 100.")
    return normalized


def normalize_exception_dates(
    *,
    start_date: date,
    target_date: date | None,
    exception_dates: list[date],
) -> list[date]:
    unique_dates = sorted(set(exception_dates))
    for exception_date in unique_dates:
        if exception_date < start_date:
            raise GoalError("Exception dates cannot be earlier than the start date.")
        if target_date is not None and exception_date > target_date:
            raise GoalError("Exception dates cannot be later than the target date.")
    return unique_dates


def create_goal(
    db: Session,
    *,
    user: User,
    metric: Metric,
    title: str,
    description: str | None,
    start_date: date,
    target_date: date | None,
    target_value_number: float | None,
    target_value_date: date | None,
    success_threshold_percent: float | None = None,
    exception_dates: list[date] | None = None,
) -> Goal:
    normalized_title = title.strip()
    if normalized_title == "":
        raise GoalError("Goal title is required.")
    if metric.user_id != user.id:
        raise GoalError("Goals can only reference your own metrics.")
    if target_date is not None and target_date < start_date:
        raise GoalError("Target date cannot be earlier than the start date.")

    normalized_exception_dates = normalize_exception_dates(
        start_date=start_date,
        target_date=target_date,
        exception_dates=exception_dates or [],
    )
    normalized_success_threshold = normalize_success_threshold_percent(success_threshold_percent)

    if metric.metric_type == METRIC_TYPE_NUMBER:
        if target_value_date is not None:
            raise GoalError("Number metrics cannot use a date target value.")
        if normalized_success_threshold is not None:
            raise GoalError("Number metrics cannot use a success threshold percent.")
        if len(normalized_exception_dates) > 0:
            raise GoalError("Number metrics cannot use exception dates.")
        if target_value_number is None:
            raise GoalError("Number metric goals require a target numeric value.")
    elif metric.metric_type == METRIC_TYPE_DATE:
        if target_value_number is not None:
            raise GoalError("Date metrics cannot use a numeric target value.")
        if target_value_date is not None:
            raise GoalError("Date metrics do not use a target metric date.")
        if target_date is None:
            raise GoalError("Date metric goals require a target date.")
        if normalized_success_threshold is None:
            normalized_success_threshold = Decimal("100.00")

    normalized_target_number: Decimal | None = None
    if metric.metric_type == METRIC_TYPE_NUMBER and target_value_number is not None:
        decimal_places = metric.decimal_places or 0
        quantizer = Decimal("1").scaleb(-decimal_places)
        normalized_target_number = Decimal(str(target_value_number)).quantize(
            quantizer,
            rounding=ROUND_HALF_UP,
        )

    goal = Goal(
        id=str(uuid4()),
        user_id=user.id,
        metric_id=metric.id,
        title=normalized_title,
        description=(
            description.strip() if description is not None and description.strip() != "" else None
        ),
        start_date=start_date,
        target_date=target_date,
        target_value_number=normalized_target_number,
        target_value_date=target_value_date,
        success_threshold_percent=normalized_success_threshold,
    )
    db.add(goal)
    db.flush()

    for exception_date in normalized_exception_dates:
        db.add(
            GoalExceptionDate(
                id=str(uuid4()),
                goal_id=goal.id,
                exception_date=exception_date,
            )
        )
    db.flush()
    return get_goal_for_user(db, user=user, goal_id=goal.id)


def get_goal_for_user(db: Session, *, user: User, goal_id: str) -> Goal:
    statement = (
        select(Goal)
        .options(
            selectinload(Goal.metric).selectinload(Metric.entries),
            selectinload(Goal.exception_dates),
        )
        .where(Goal.id == goal_id, Goal.user_id == user.id)
    )
    goal = db.scalar(statement)
    if goal is None:
        raise GoalNotFoundError("Goal was not found.")
    return goal


def get_latest_metric_entry(metric: Metric) -> MetricEntry | None:
    if len(metric.entries) == 0:
        return None
    return metric.entries[0]


def goal_exception_date_values(goal: Goal) -> set[date]:
    return {exception_date.exception_date for exception_date in goal.exception_dates}


def normalize_metric_entry_recorded_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def goal_entry_effective_date(entry: MetricEntry) -> date:
    if entry.date_value is not None:
        return entry.date_value
    return normalize_metric_entry_recorded_at(entry.recorded_at).date()


def get_user_timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")


def goal_start_cutoff(goal: Goal) -> datetime:
    user_timezone = get_user_timezone(goal.user)
    return datetime.combine(goal.start_date, time.min, tzinfo=user_timezone).astimezone(UTC)


def sort_metric_entries_ascending(entries: list[MetricEntry]) -> list[MetricEntry]:
    return sorted(entries, key=lambda entry: normalize_metric_entry_recorded_at(entry.recorded_at))


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
    start_cutoff = goal_start_cutoff(goal)
    baseline_entry: MetricEntry | None = None
    first_after_start: MetricEntry | None = None

    for entry in ordered_entries:
        recorded_at = normalize_metric_entry_recorded_at(entry.recorded_at)
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

    comparison_date = as_of_date or datetime.now(UTC).date()
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

    start_cutoff = goal_start_cutoff(goal)
    current_entry = baseline_entry
    for entry in ordered_entries:
        if normalize_metric_entry_recorded_at(entry.recorded_at) >= start_cutoff:
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

    start_cutoff = goal_start_cutoff(goal)
    current_entry = baseline_entry
    for entry in ordered_entries:
        if normalize_metric_entry_recorded_at(entry.recorded_at) >= start_cutoff:
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
    if goal.target_date is None:
        return None

    comparison_time = as_of or datetime.now(UTC)
    start_time = datetime.combine(goal.start_date, time.min, tzinfo=UTC)
    end_time = datetime.combine(goal.target_date + timedelta(days=1), time.min, tzinfo=UTC)

    if comparison_time <= start_time:
        return 0.0
    if comparison_time >= end_time:
        return 100.0

    total_seconds = (end_time - start_time).total_seconds()
    if total_seconds <= 0:
        return 100.0

    elapsed_seconds = (comparison_time - start_time).total_seconds()
    return round(max(0.0, min((elapsed_seconds / total_seconds) * 100, 100.0)), 2)


def goal_failure_risk_percent(goal: Goal) -> float | None:
    success_percent = goal_current_progress_percent(goal)
    time_completion_percent = goal_time_completion_percent(goal)
    if success_percent is None or time_completion_percent is None:
        return None
    return round(max(0.0, time_completion_percent - success_percent), 2)


@dataclass
class GoalDateProgressPoint:
    recorded_at: datetime
    progress_percent: float


def build_goal_date_progress_points(goal: Goal) -> list[GoalDateProgressPoint]:
    if goal.metric.metric_type != METRIC_TYPE_DATE or goal.target_date is None:
        return []

    today = datetime.now(UTC).date()
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
