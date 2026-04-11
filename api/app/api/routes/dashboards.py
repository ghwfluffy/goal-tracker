from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db import Dashboard, DashboardWidget, Goal, Metric, MetricEntry, User, get_db
from app.services.dashboards import (
    DashboardError,
    DashboardNotFoundError,
    DashboardWidgetNotFoundError,
    build_goal_progress_points,
    create_dashboard,
    create_dashboard_widget,
    delete_dashboard,
    delete_dashboard_widget,
    filter_entries_to_window,
    get_dashboard_for_user,
    get_dashboard_widget_for_user,
    get_widget_current_progress_percent,
    get_widget_target_met,
    list_dashboards_for_user,
    update_dashboard,
    update_dashboard_widget,
)
from app.services.goals import GoalNotFoundError, get_goal_for_user
from app.services.metrics import MetricNotFoundError, get_metric_for_user

router = APIRouter(prefix="/dashboards")

MetricType = Literal["integer", "date"]
WidgetType = Literal["metric_history", "metric_summary", "goal_progress", "goal_summary"]


class MetricEntrySummary(BaseModel):
    id: str
    recorded_at: str
    integer_value: int | None
    date_value: str | None


class MetricReferenceSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    unit_label: str | None
    latest_entry: MetricEntrySummary | None


class GoalReferenceSummary(BaseModel):
    id: str
    title: str
    start_date: str
    target_date: str | None
    target_value_integer: int | None
    target_value_date: str | None
    metric: MetricReferenceSummary


class WidgetSeriesPoint(BaseModel):
    recorded_at: str
    integer_value: int | None
    date_value: str | None
    progress_percent: float | None


class WidgetSummary(BaseModel):
    id: str
    title: str
    widget_type: WidgetType
    display_order: int
    rolling_window_days: int | None
    metric: MetricReferenceSummary | None
    goal: GoalReferenceSummary | None
    current_progress_percent: float | None
    target_met: bool | None
    series: list[WidgetSeriesPoint]


class DashboardSummary(BaseModel):
    id: str
    name: str
    description: str | None
    is_default: bool
    widgets: list[WidgetSummary]


class DashboardListResponse(BaseModel):
    dashboards: list[DashboardSummary]


class CreateDashboardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    make_default: bool = False


class UpdateDashboardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    make_default: bool | None = None


class CreateWidgetRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    widget_type: WidgetType
    metric_id: str | None = None
    goal_id: str | None = None
    rolling_window_days: int | None = Field(default=None, ge=1, le=3650)

    @model_validator(mode="after")
    def validate_subject(self) -> CreateWidgetRequest:
        is_metric_widget = self.widget_type in {"metric_history", "metric_summary"}
        if is_metric_widget and (self.metric_id is None or self.goal_id is not None):
            raise ValueError("Metric widgets require metric_id and cannot include goal_id.")
        if not is_metric_widget and (self.goal_id is None or self.metric_id is not None):
            raise ValueError("Goal widgets require goal_id and cannot include metric_id.")
        return self


class UpdateWidgetRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    rolling_window_days: int | None = Field(default=None, ge=1, le=3650)


def serialize_metric_entry(entry: MetricEntry) -> MetricEntrySummary:
    return MetricEntrySummary(
        id=entry.id,
        recorded_at=entry.recorded_at.isoformat(),
        integer_value=entry.integer_value,
        date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
    )


def serialize_metric_reference(metric: Metric) -> MetricReferenceSummary:
    latest_entry = metric.entries[0] if len(metric.entries) > 0 else None
    return MetricReferenceSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        unit_label=metric.unit_label,
        latest_entry=serialize_metric_entry(latest_entry) if latest_entry is not None else None,
    )


def serialize_goal_reference(goal: Goal) -> GoalReferenceSummary:
    return GoalReferenceSummary(
        id=goal.id,
        title=goal.title,
        start_date=goal.start_date.isoformat(),
        target_date=goal.target_date.isoformat() if goal.target_date is not None else None,
        target_value_integer=goal.target_value_integer,
        target_value_date=(
            goal.target_value_date.isoformat() if goal.target_value_date is not None else None
        ),
        metric=serialize_metric_reference(goal.metric),
    )


def serialize_widget_series(widget: DashboardWidget) -> list[WidgetSeriesPoint]:
    if widget.metric is not None:
        entries = filter_entries_to_window(
            widget.metric.entries,
            rolling_window_days=widget.rolling_window_days,
        )
        return [
            WidgetSeriesPoint(
                recorded_at=entry.recorded_at.isoformat(),
                integer_value=entry.integer_value,
                date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
                progress_percent=None,
            )
            for entry in entries
        ]

    if widget.goal is not None:
        return [
            WidgetSeriesPoint(
                recorded_at=point.entry.recorded_at.isoformat(),
                integer_value=point.entry.integer_value,
                date_value=(
                    point.entry.date_value.isoformat()
                    if point.entry.date_value is not None
                    else None
                ),
                progress_percent=round(point.progress_percent, 2),
            )
            for point in build_goal_progress_points(
                widget.goal,
                rolling_window_days=widget.rolling_window_days,
            )
        ]

    return []


def serialize_widget(widget: DashboardWidget) -> WidgetSummary:
    current_progress_percent = get_widget_current_progress_percent(widget)
    return WidgetSummary(
        id=widget.id,
        title=widget.title,
        widget_type=cast(WidgetType, widget.widget_type),
        display_order=widget.display_order,
        rolling_window_days=widget.rolling_window_days,
        metric=serialize_metric_reference(widget.metric) if widget.metric is not None else None,
        goal=serialize_goal_reference(widget.goal) if widget.goal is not None else None,
        current_progress_percent=(
            round(current_progress_percent, 2) if current_progress_percent is not None else None
        ),
        target_met=get_widget_target_met(widget),
        series=serialize_widget_series(widget),
    )


def serialize_dashboard(dashboard: Dashboard, *, user: User) -> DashboardSummary:
    return DashboardSummary(
        id=dashboard.id,
        name=dashboard.name,
        description=dashboard.description,
        is_default=user.default_dashboard_id == dashboard.id,
        widgets=[serialize_widget(widget) for widget in dashboard.widgets],
    )


@router.get("", response_model=DashboardListResponse)
def get_dashboards(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardListResponse:
    dashboards = list_dashboards_for_user(db, user)
    return DashboardListResponse(
        dashboards=[serialize_dashboard(dashboard, user=user) for dashboard in dashboards]
    )


@router.post("", response_model=DashboardSummary, status_code=status.HTTP_201_CREATED)
def post_dashboard(
    payload: CreateDashboardRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    try:
        dashboard = create_dashboard(
            db,
            user=user,
            name=payload.name,
            description=payload.description,
            make_default=payload.make_default,
        )
        db.commit()
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_dashboard(dashboard, user=user)


@router.patch("/{dashboard_id}", response_model=DashboardSummary)
def patch_dashboard(
    dashboard_id: str,
    payload: UpdateDashboardRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        updated_dashboard = update_dashboard(
            db,
            dashboard=dashboard,
            user=user,
            name=payload.name,
            description=payload.description,
            make_default=payload.make_default,
        )
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_dashboard(updated_dashboard, user=user)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dashboard(
    dashboard_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        delete_dashboard(db, dashboard=dashboard, user=user)
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{dashboard_id}/widgets",
    response_model=WidgetSummary,
    status_code=status.HTTP_201_CREATED,
)
def post_dashboard_widget(
    dashboard_id: str,
    payload: CreateWidgetRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WidgetSummary:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        metric = (
            get_metric_for_user(db, user=user, metric_id=payload.metric_id)
            if payload.metric_id is not None
            else None
        )
        goal = (
            get_goal_for_user(db, user=user, goal_id=payload.goal_id)
            if payload.goal_id is not None
            else None
        )
        widget = create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=payload.title,
            widget_type=payload.widget_type,
            metric=metric,
            goal=goal,
            rolling_window_days=payload.rolling_window_days,
        )
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetricNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_widget(widget)


@router.patch("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetSummary)
def patch_dashboard_widget(
    dashboard_id: str,
    widget_id: str,
    payload: UpdateWidgetRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WidgetSummary:
    try:
        widget = get_dashboard_widget_for_user(
            db,
            user=user,
            dashboard_id=dashboard_id,
            widget_id=widget_id,
        )
        updated_widget = update_dashboard_widget(
            db,
            widget=widget,
            user=user,
            title=payload.title,
            rolling_window_days=payload.rolling_window_days,
        )
        db.commit()
    except DashboardWidgetNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_widget(updated_widget)


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dashboard_widget(
    dashboard_id: str,
    widget_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        widget = get_dashboard_widget_for_user(
            db,
            user=user,
            dashboard_id=dashboard_id,
            widget_id=widget_id,
        )
        delete_dashboard_widget(db, widget=widget)
        db.commit()
    except DashboardWidgetNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
