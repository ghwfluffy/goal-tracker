from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db import Goal, GoalChecklistItem, Metric, MetricEntry, User, get_db
from app.services.goals import (
    GOAL_TYPE_METRIC,
    ChecklistItemInput,
    GoalChecklistItemNotFoundError,
    GoalError,
    GoalNotFoundError,
    create_goal,
    get_goal_checklist_item_for_user,
    get_goal_for_user,
    goal_current_progress_percent,
    goal_failure_risk_percent,
    goal_target_met,
    goal_time_completion_percent,
    list_goals_for_user,
    set_goal_checklist_item_completed,
    update_goal,
)
from app.services.metrics import (
    MetricError,
    MetricNotFoundError,
    create_metric,
    get_metric_for_user,
)

router = APIRouter(prefix="/goals")

MetricType = Literal["number", "date"]
GoalType = Literal["metric", "checklist"]


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


class GoalChecklistItemSummary(BaseModel):
    id: str
    title: str
    display_order: int
    is_completed: bool
    completed_at: str | None


class GoalSummary(BaseModel):
    archived_at: str | None
    id: str
    goal_type: GoalType
    is_archived: bool
    title: str
    description: str | None
    status: str
    start_date: str
    target_date: str | None
    target_value_number: float | None
    target_value_date: str | None
    success_threshold_percent: float | None
    exception_dates: list[str]
    checklist_items: list[GoalChecklistItemSummary]
    checklist_total_count: int
    checklist_completed_count: int
    current_progress_percent: float | None
    time_progress_percent: float | None
    failure_risk_percent: float | None
    target_met: bool | None
    metric: GoalMetricSummary | None


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


class ChecklistItemRequest(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=160)


class CreateGoalRequest(BaseModel):
    goal_type: GoalType = cast(GoalType, GOAL_TYPE_METRIC)
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    start_date: date
    target_date: date | None = None
    target_value_number: float | None = None
    target_value_date: date | None = None
    success_threshold_percent: float | None = Field(default=None, ge=0, le=100)
    exception_dates: list[date] = Field(default_factory=list)
    checklist_items: list[ChecklistItemRequest] = Field(default_factory=list)
    metric_id: str | None = None
    new_metric: InlineMetricRequest | None = None

    @model_validator(mode="after")
    def validate_goal_shape(self) -> CreateGoalRequest:
        has_metric_id = self.metric_id is not None and self.metric_id.strip() != ""
        has_new_metric = self.new_metric is not None
        if self.goal_type == GOAL_TYPE_METRIC:
            if has_metric_id == has_new_metric:
                raise ValueError("Metric goals must provide either metric_id or new_metric.")
            if len(self.checklist_items) > 0:
                raise ValueError("Metric goals cannot include checklist items.")
        else:
            if has_metric_id or has_new_metric:
                raise ValueError("Checklist goals cannot include metric fields.")
            if len(self.checklist_items) == 0:
                raise ValueError("Checklist goals require at least one checklist item.")
        return self


class UpdateGoalRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    description: str | None = None
    start_date: date | None = None
    target_date: date | None = None
    target_value_number: float | None = None
    target_value_date: date | None = None
    success_threshold_percent: float | None = Field(default=None, ge=0, le=100)
    exception_dates: list[date] | None = None
    checklist_items: list[ChecklistItemRequest] | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_update_payload(self) -> UpdateGoalRequest:
        if len(self.model_fields_set) == 0:
            raise ValueError("Provide at least one goal field to update.")
        if "title" in self.model_fields_set and (self.title is None or self.title.strip() == ""):
            raise ValueError("Goal title is required.")
        return self


class UpdateChecklistItemCompletionRequest(BaseModel):
    completed: bool


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


def serialize_goal_checklist_item(item: GoalChecklistItem) -> GoalChecklistItemSummary:
    return GoalChecklistItemSummary(
        id=item.id,
        title=item.title,
        display_order=item.display_order,
        is_completed=item.completed_at is not None,
        completed_at=item.completed_at.isoformat() if item.completed_at is not None else None,
    )


def serialize_goal(goal: Goal) -> GoalSummary:
    checklist_items = [serialize_goal_checklist_item(item) for item in goal.checklist_items]
    checklist_completed_count = sum(1 for item in checklist_items if item.is_completed)
    return GoalSummary(
        archived_at=goal.archived_at.isoformat() if goal.archived_at is not None else None,
        id=goal.id,
        goal_type=cast(GoalType, goal.goal_type),
        is_archived=goal.archived_at is not None,
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
        checklist_items=checklist_items,
        checklist_total_count=len(checklist_items),
        checklist_completed_count=checklist_completed_count,
        current_progress_percent=goal_current_progress_percent(goal),
        time_progress_percent=goal_time_completion_percent(goal),
        failure_risk_percent=goal_failure_risk_percent(goal),
        target_met=goal_target_met(goal),
        metric=serialize_goal_metric(goal.metric) if goal.metric is not None else None,
    )


@router.get("", response_model=GoalListResponse)
def get_goals(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    include_archived: Annotated[bool, Query()] = False,
) -> GoalListResponse:
    return GoalListResponse(
        goals=[
            serialize_goal(goal) for goal in list_goals_for_user(db, user, include_archived=include_archived)
        ]
    )


@router.post("", response_model=GoalSummary, status_code=status.HTTP_201_CREATED)
def post_goal(
    payload: CreateGoalRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GoalSummary:
    try:
        metric: Metric | None
        if payload.goal_type == GOAL_TYPE_METRIC:
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
                raise GoalError("Metric goals must reference a metric.")
        else:
            metric = None

        goal = create_goal(
            db,
            user=user,
            goal_type=payload.goal_type,
            metric=metric,
            title=payload.title,
            description=payload.description,
            start_date=payload.start_date,
            target_date=payload.target_date,
            target_value_number=payload.target_value_number,
            target_value_date=payload.target_value_date,
            success_threshold_percent=payload.success_threshold_percent,
            exception_dates=payload.exception_dates,
            checklist_items=[
                ChecklistItemInput(id=item.id, title=item.title) for item in payload.checklist_items
            ],
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


@router.patch("/{goal_id}", response_model=GoalSummary)
def patch_goal(
    goal_id: str,
    payload: UpdateGoalRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GoalSummary:
    try:
        goal = get_goal_for_user(db, user=user, goal_id=goal_id)
        updated_goal = update_goal(
            db,
            goal=goal,
            update_fields=payload.model_fields_set,
            title=payload.title,
            description=payload.description,
            start_date=payload.start_date,
            target_date=payload.target_date,
            target_value_number=payload.target_value_number,
            target_value_date=payload.target_value_date,
            success_threshold_percent=payload.success_threshold_percent,
            exception_dates=payload.exception_dates,
            checklist_items=(
                [ChecklistItemInput(id=item.id, title=item.title) for item in payload.checklist_items]
                if payload.checklist_items is not None
                else None
            ),
            archived=payload.archived,
        )
        db.commit()
    except GoalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_goal(updated_goal)


@router.patch("/{goal_id}/checklist-items/{item_id}", response_model=GoalSummary)
def patch_goal_checklist_item(
    goal_id: str,
    item_id: str,
    payload: UpdateChecklistItemCompletionRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GoalSummary:
    try:
        goal = get_goal_for_user(db, user=user, goal_id=goal_id)
        checklist_item = get_goal_checklist_item_for_user(
            db,
            user=user,
            goal_id=goal_id,
            item_id=item_id,
        )
        updated_goal = set_goal_checklist_item_completed(
            db,
            goal=goal,
            checklist_item=checklist_item,
            completed=payload.completed,
        )
        db.commit()
    except GoalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalChecklistItemNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_goal(updated_goal)
