from __future__ import annotations

from decimal import Decimal
from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from app.db import Dashboard, DashboardWidget, Goal, Metric, MetricEntry, User
from app.services.dashboard_layout import METRIC_WIDGET_TYPES
from app.services.dashboards import filter_entries_to_window
from app.services.goal_progress import (
    build_goal_progress_points,
    goal_current_progress_percent,
    goal_failure_risk_percent,
    goal_target_met,
    goal_time_completion_percent,
)

MetricType = Literal["number", "date"]
ForecastAlgorithm = Literal[
    "simple",
    "weighted_week_over_week",
    "weighted_day_over_day",
]
LayoutMode = Literal["desktop", "mobile"]
WidgetType = Literal[
    "metric_history",
    "metric_summary",
    "days_since",
    "goal_progress",
    "goal_summary",
    "goal_completion_percent",
    "goal_success_percent",
    "goal_failure_risk",
]


class MetricEntrySummary(BaseModel):
    id: str
    recorded_at: str
    number_value: float | None
    date_value: str | None


class MetricReferenceSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    decimal_places: int | None
    unit_label: str | None
    latest_entry: MetricEntrySummary | None


class GoalReferenceSummary(BaseModel):
    id: str
    title: str
    start_date: str
    target_date: str | None
    target_value_number: float | None
    target_value_date: str | None
    success_threshold_percent: float | None
    exception_dates: list[str]
    metric: MetricReferenceSummary


class WidgetSeriesPoint(BaseModel):
    recorded_at: str
    number_value: float | None
    date_value: str | None
    progress_percent: float | None


class WidgetSummary(BaseModel):
    id: str
    title: str
    widget_type: WidgetType
    display_order: int
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int
    mobile_grid_x: int
    mobile_grid_y: int
    mobile_grid_w: int
    mobile_grid_h: int
    rolling_window_days: int | None
    forecast_algorithm: ForecastAlgorithm | None
    metric: MetricReferenceSummary | None
    goal: GoalReferenceSummary | None
    current_progress_percent: float | None
    time_completion_percent: float | None
    failure_risk_percent: float | None
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
    forecast_algorithm: ForecastAlgorithm | None = None
    grid_x: int | None = Field(default=None, ge=0, le=11)
    grid_y: int | None = Field(default=None, ge=0, le=10000)
    grid_w: int | None = Field(default=None, ge=1, le=12)
    grid_h: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def validate_subject(self) -> CreateWidgetRequest:
        is_metric_widget = self.widget_type in METRIC_WIDGET_TYPES
        if is_metric_widget and (self.metric_id is None or self.goal_id is not None):
            raise ValueError("Metric widgets require metric_id and cannot include goal_id.")
        if not is_metric_widget and (self.goal_id is None or self.metric_id is not None):
            raise ValueError("Goal widgets require goal_id and cannot include metric_id.")
        return self


class UpdateWidgetRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    rolling_window_days: int | None = Field(default=None, ge=1, le=3650)
    forecast_algorithm: ForecastAlgorithm | None = None
    layout_mode: LayoutMode | None = None
    grid_x: int | None = Field(default=None, ge=0, le=11)
    grid_y: int | None = Field(default=None, ge=0, le=10000)
    grid_w: int | None = Field(default=None, ge=1, le=12)
    grid_h: int | None = Field(default=None, ge=1, le=12)


def decimal_to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def serialize_metric_entry(entry: MetricEntry) -> MetricEntrySummary:
    return MetricEntrySummary(
        id=entry.id,
        recorded_at=entry.recorded_at.isoformat(),
        number_value=decimal_to_float(entry.number_value),
        date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
    )


def serialize_metric_reference(metric: Metric) -> MetricReferenceSummary:
    latest_entry = metric.entries[0] if len(metric.entries) > 0 else None
    return MetricReferenceSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        decimal_places=metric.decimal_places,
        unit_label=metric.unit_label,
        latest_entry=serialize_metric_entry(latest_entry) if latest_entry is not None else None,
    )


def serialize_goal_reference(goal: Goal) -> GoalReferenceSummary:
    return GoalReferenceSummary(
        id=goal.id,
        title=goal.title,
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
                number_value=decimal_to_float(entry.number_value),
                date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
                progress_percent=None,
            )
            for entry in entries
        ]

    if widget.goal is not None:
        return [
            WidgetSeriesPoint(
                recorded_at=point.recorded_at.isoformat(),
                number_value=decimal_to_float(point.number_value),
                date_value=point.date_value.isoformat() if point.date_value is not None else None,
                progress_percent=point.progress_percent,
            )
            for point in build_goal_progress_points(
                widget.goal,
                rolling_window_days=widget.rolling_window_days,
            )
        ]

    return []


def serialize_widget(widget: DashboardWidget) -> WidgetSummary:
    current_progress_percent = goal_current_progress_percent(widget.goal) if widget.goal is not None else None
    time_completion_percent = goal_time_completion_percent(widget.goal) if widget.goal is not None else None
    failure_risk_percent = goal_failure_risk_percent(widget.goal) if widget.goal is not None else None
    target_met = goal_target_met(widget.goal) if widget.goal is not None else None

    return WidgetSummary(
        id=widget.id,
        title=widget.title,
        widget_type=cast(WidgetType, widget.widget_type),
        display_order=widget.display_order,
        grid_x=widget.grid_x,
        grid_y=widget.grid_y,
        grid_w=widget.grid_w,
        grid_h=widget.grid_h,
        mobile_grid_x=widget.mobile_grid_x,
        mobile_grid_y=widget.mobile_grid_y,
        mobile_grid_w=widget.mobile_grid_w,
        mobile_grid_h=widget.mobile_grid_h,
        rolling_window_days=widget.rolling_window_days,
        forecast_algorithm=cast(ForecastAlgorithm | None, widget.forecast_algorithm),
        metric=serialize_metric_reference(widget.metric) if widget.metric is not None else None,
        goal=serialize_goal_reference(widget.goal) if widget.goal is not None else None,
        current_progress_percent=current_progress_percent,
        time_completion_percent=time_completion_percent,
        failure_risk_percent=failure_risk_percent,
        target_met=target_met,
        series=serialize_widget_series(widget),
    )


def serialize_dashboard(dashboard: Dashboard, *, user: User) -> DashboardSummary:
    return DashboardSummary(
        id=dashboard.id,
        name=dashboard.name,
        description=dashboard.description,
        is_default=user.default_dashboard_id == dashboard.id,
        widgets=[
            serialize_widget(widget)
            for widget in sorted(
                dashboard.widgets,
                key=lambda widget: (widget.grid_y, widget.grid_x, widget.display_order),
            )
        ],
    )
