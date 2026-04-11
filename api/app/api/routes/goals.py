from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db import Goal, Metric, MetricEntry, User, get_db
from app.services.goals import (
    GoalError,
    create_goal,
    goal_current_progress_percent,
    goal_failure_risk_percent,
    goal_target_met,
    goal_time_completion_percent,
    list_goals_for_user,
)
from app.services.metrics import (
    MetricError,
    MetricNotFoundError,
    create_metric,
    get_metric_for_user,
)

router = APIRouter(prefix="/goals")

MetricType = Literal["number", "date"]


class GoalMetricEntrySummary(BaseModel):
    id: str
    recorded_at: str
    number_value: float | None
    date_value: str | None


class GoalMetricSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    decimal_places: int | None
    unit_label: str | None
    latest_entry: GoalMetricEntrySummary | None


class GoalSummary(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    start_date: str
    target_date: str | None
    target_value_number: float | None
    target_value_date: str | None
    success_threshold_percent: float | None
    exception_dates: list[str]
    current_progress_percent: float | None
    time_progress_percent: float | None
    failure_risk_percent: float | None
    target_met: bool | None
    metric: GoalMetricSummary


class GoalListResponse(BaseModel):
    goals: list[GoalSummary]


class InlineMetricRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    metric_type: MetricType
    decimal_places: int | None = Field(default=None, ge=0, le=6)
    unit_label: str | None = Field(default=None, max_length=40)
    initial_number_value: float | None = None
    initial_date_value: date | None = None
    recorded_at: datetime | None = None


class CreateGoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    start_date: date
    target_date: date | None = None
    target_value_number: float | None = None
    target_value_date: date | None = None
    success_threshold_percent: float | None = Field(default=None, ge=0, le=100)
    exception_dates: list[date] = Field(default_factory=list)
    metric_id: str | None = None
    new_metric: InlineMetricRequest | None = None

    @model_validator(mode="after")
    def validate_metric_selection(self) -> CreateGoalRequest:
        has_metric_id = self.metric_id is not None and self.metric_id.strip() != ""
        has_new_metric = self.new_metric is not None
        if has_metric_id == has_new_metric:
            raise ValueError("Provide either metric_id or new_metric.")
        return self


def decimal_to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def serialize_metric_entry(entry: MetricEntry) -> GoalMetricEntrySummary:
    return GoalMetricEntrySummary(
        id=entry.id,
        recorded_at=entry.recorded_at.isoformat(),
        number_value=decimal_to_float(entry.number_value),
        date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
    )


def serialize_goal_metric(metric: Metric) -> GoalMetricSummary:
    latest_entry = metric.entries[0] if len(metric.entries) > 0 else None
    return GoalMetricSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        decimal_places=metric.decimal_places,
        unit_label=metric.unit_label,
        latest_entry=serialize_metric_entry(latest_entry) if latest_entry is not None else None,
    )


def serialize_goal(goal: Goal) -> GoalSummary:
    return GoalSummary(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        status=goal.status,
        start_date=goal.start_date.isoformat(),
        target_date=goal.target_date.isoformat() if goal.target_date is not None else None,
        target_value_number=decimal_to_float(goal.target_value_number),
        target_value_date=(
            goal.target_value_date.isoformat() if goal.target_value_date is not None else None
        ),
        success_threshold_percent=decimal_to_float(goal.success_threshold_percent),
        exception_dates=[
            exception_date.exception_date.isoformat() for exception_date in goal.exception_dates
        ],
        current_progress_percent=goal_current_progress_percent(goal),
        time_progress_percent=goal_time_completion_percent(goal),
        failure_risk_percent=goal_failure_risk_percent(goal),
        target_met=goal_target_met(goal),
        metric=serialize_goal_metric(goal.metric),
    )


@router.get("", response_model=GoalListResponse)
def get_goals(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GoalListResponse:
    return GoalListResponse(goals=[serialize_goal(goal) for goal in list_goals_for_user(db, user)])


@router.post("", response_model=GoalSummary, status_code=status.HTTP_201_CREATED)
def post_goal(
    payload: CreateGoalRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GoalSummary:
    try:
        if payload.metric_id is not None and payload.metric_id.strip() != "":
            metric = get_metric_for_user(db, user=user, metric_id=payload.metric_id)
        elif payload.new_metric is not None:
            metric = create_metric(
                db,
                user=user,
                name=payload.new_metric.name,
                metric_type=payload.new_metric.metric_type,
                decimal_places=payload.new_metric.decimal_places,
                unit_label=payload.new_metric.unit_label,
                initial_number_value=payload.new_metric.initial_number_value,
                initial_date_value=payload.new_metric.initial_date_value,
                recorded_at=payload.new_metric.recorded_at,
            )
        else:
            raise GoalError("Goal must reference a metric.")

        goal = create_goal(
            db,
            user=user,
            metric=metric,
            title=payload.title,
            description=payload.description,
            start_date=payload.start_date,
            target_date=payload.target_date,
            target_value_number=payload.target_value_number,
            target_value_date=payload.target_value_date,
            success_threshold_percent=payload.success_threshold_percent,
            exception_dates=payload.exception_dates,
        )
        db.commit()
    except MetricError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except MetricNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_goal(goal)
