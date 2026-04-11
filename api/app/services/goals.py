from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Goal, Metric, MetricEntry, User


class GoalError(Exception):
    pass


class GoalNotFoundError(Exception):
    pass


def list_goals_for_user(db: Session, user: User) -> list[Goal]:
    statement = (
        select(Goal)
        .options(selectinload(Goal.metric).selectinload(Metric.entries))
        .where(Goal.user_id == user.id)
        .order_by(Goal.created_at.desc())
    )
    return list(db.scalars(statement))


def create_goal(
    db: Session,
    *,
    user: User,
    metric: Metric,
    title: str,
    description: str | None,
    start_date: date,
    target_date: date | None,
    target_value_integer: int | None,
    target_value_date: date | None,
) -> Goal:
    normalized_title = title.strip()
    if normalized_title == "":
        raise GoalError("Goal title is required.")
    if metric.user_id != user.id:
        raise GoalError("Goals can only reference your own metrics.")
    if target_date is not None and target_date < start_date:
        raise GoalError("Target date cannot be earlier than the start date.")

    if metric.metric_type == "integer":
        if target_value_date is not None:
            raise GoalError("Integer metrics cannot use a date target value.")
    elif metric.metric_type == "date":
        if target_value_integer is not None:
            raise GoalError("Date metrics cannot use an integer target value.")

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
        target_value_integer=target_value_integer,
        target_value_date=target_value_date,
    )
    db.add(goal)
    db.flush()
    return get_goal_for_user(db, user=user, goal_id=goal.id)


def get_goal_for_user(db: Session, *, user: User, goal_id: str) -> Goal:
    statement = (
        select(Goal)
        .options(selectinload(Goal.metric).selectinload(Metric.entries))
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
