from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Goal, GoalExceptionDate, Metric, User
from app.services import goal_progress
from app.services.metrics import METRIC_TYPE_DATE, METRIC_TYPE_NUMBER


class GoalError(Exception):
    pass


class GoalNotFoundError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


build_goal_date_progress_points = goal_progress.build_goal_date_progress_points
goal_current_progress_percent = goal_progress.goal_current_progress_percent
goal_failure_risk_percent = goal_progress.goal_failure_risk_percent
goal_progress_as_of_date = goal_progress.goal_progress_as_of_date
goal_target_met = goal_progress.goal_target_met
goal_time_completion_percent = goal_progress.goal_time_completion_percent


def list_goals_for_user(db: Session, user: User, *, include_archived: bool = False) -> list[Goal]:
    statement = (
        select(Goal)
        .options(
            selectinload(Goal.metric).selectinload(Metric.entries),
            selectinload(Goal.exception_dates),
            selectinload(Goal.user),
        )
        .where(Goal.user_id == user.id)
        .order_by(Goal.created_at.desc())
    )
    if not include_archived:
        statement = statement.where(Goal.archived_at.is_(None))
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


def normalize_goal_details(
    *,
    metric: Metric,
    title: str,
    description: str | None,
    start_date: date,
    target_date: date | None,
    target_value_number: float | None,
    target_value_date: date | None,
    success_threshold_percent: float | None,
    exception_dates: list[date],
) -> tuple[str, str | None, date | None, Decimal | None, date | None, Decimal | None, list[date]]:
    normalized_title = title.strip()
    if normalized_title == "":
        raise GoalError("Goal title is required.")
    if target_date is not None and target_date < start_date:
        raise GoalError("Target date cannot be earlier than the start date.")

    normalized_description = (
        description.strip() if description is not None and description.strip() != "" else None
    )
    normalized_exception_dates = normalize_exception_dates(
        start_date=start_date,
        target_date=target_date,
        exception_dates=exception_dates,
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

    return (
        normalized_title,
        normalized_description,
        target_date,
        normalized_target_number,
        target_value_date,
        normalized_success_threshold,
        normalized_exception_dates,
    )


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
    if metric.user_id != user.id:
        raise GoalError("Goals can only reference your own metrics.")
    (
        normalized_title,
        normalized_description,
        normalized_target_date,
        normalized_target_number,
        normalized_target_value_date,
        normalized_success_threshold,
        normalized_exception_dates,
    ) = normalize_goal_details(
        metric=metric,
        title=title,
        description=description,
        start_date=start_date,
        target_date=target_date,
        target_value_number=target_value_number,
        target_value_date=target_value_date,
        success_threshold_percent=success_threshold_percent,
        exception_dates=exception_dates or [],
    )

    goal = Goal(
        id=str(uuid4()),
        user_id=user.id,
        metric_id=metric.id,
        title=normalized_title,
        description=normalized_description,
        start_date=start_date,
        target_date=normalized_target_date,
        target_value_number=normalized_target_number,
        target_value_date=normalized_target_value_date,
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
            selectinload(Goal.user),
        )
        .where(Goal.id == goal_id, Goal.user_id == user.id)
    )
    goal = db.scalar(statement)
    if goal is None:
        raise GoalNotFoundError("Goal was not found.")
    return goal


def update_goal(
    db: Session,
    *,
    goal: Goal,
    update_fields: set[str],
    title: str | None = None,
    description: str | None = None,
    start_date: date | None = None,
    target_date: date | None = None,
    target_value_number: float | None = None,
    target_value_date: date | None = None,
    success_threshold_percent: float | None = None,
    exception_dates: list[date] | None = None,
    archived: bool | None = None,
) -> Goal:
    resolved_title = title if "title" in update_fields else goal.title
    resolved_description = description if "description" in update_fields else goal.description
    resolved_start_date = start_date if "start_date" in update_fields else goal.start_date
    resolved_target_date = target_date if "target_date" in update_fields else goal.target_date
    resolved_target_value_number = (
        target_value_number if "target_value_number" in update_fields else goal.target_value_number
    )
    resolved_target_value_date = (
        target_value_date if "target_value_date" in update_fields else goal.target_value_date
    )
    resolved_success_threshold_percent = (
        success_threshold_percent
        if "success_threshold_percent" in update_fields
        else goal.success_threshold_percent
    )
    resolved_exception_dates = (
        exception_dates
        if "exception_dates" in update_fields
        else [exception_date.exception_date for exception_date in goal.exception_dates]
    )

    normalized_title_input = cast(str, resolved_title)
    normalized_start_date_input = cast(date, resolved_start_date)
    normalized_exception_dates_input = cast(list[date], resolved_exception_dates)

    (
        normalized_title,
        normalized_description,
        normalized_target_date,
        normalized_target_number,
        normalized_target_value_date,
        normalized_success_threshold,
        normalized_exception_dates,
    ) = normalize_goal_details(
        metric=goal.metric,
        title=normalized_title_input,
        description=resolved_description,
        start_date=normalized_start_date_input,
        target_date=resolved_target_date,
        target_value_number=(
            float(resolved_target_value_number) if resolved_target_value_number is not None else None
        ),
        target_value_date=resolved_target_value_date,
        success_threshold_percent=(
            float(resolved_success_threshold_percent)
            if resolved_success_threshold_percent is not None
            else None
        ),
        exception_dates=normalized_exception_dates_input,
    )

    goal.title = normalized_title
    goal.description = normalized_description
    goal.start_date = normalized_start_date_input
    goal.target_date = normalized_target_date
    goal.target_value_number = (
        float(normalized_target_number) if normalized_target_number is not None else None
    )
    goal.target_value_date = normalized_target_value_date
    goal.success_threshold_percent = (
        float(normalized_success_threshold) if normalized_success_threshold is not None else None
    )
    if "archived" in update_fields:
        goal.archived_at = utcnow() if archived else None

    goal.exception_dates.clear()
    for exception_date in normalized_exception_dates:
        goal.exception_dates.append(
            GoalExceptionDate(
                id=str(uuid4()),
                goal_id=goal.id,
                exception_date=exception_date,
            )
        )

    goal.updated_at = utcnow()
    db.flush()
    return get_goal_for_user(db, user=goal.user, goal_id=goal.id)
