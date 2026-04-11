from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Dashboard, DashboardWidget, Goal, Metric, MetricEntry, User
from app.services.goals import (
    build_goal_date_progress_points,
    goal_progress_as_of_date,
    goal_target_met,
)

WIDGET_TYPE_METRIC_HISTORY = "metric_history"
WIDGET_TYPE_METRIC_SUMMARY = "metric_summary"
WIDGET_TYPE_GOAL_PROGRESS = "goal_progress"
WIDGET_TYPE_GOAL_SUMMARY = "goal_summary"
WIDGET_TYPE_GOAL_COMPLETION_PERCENT = "goal_completion_percent"
WIDGET_TYPE_GOAL_SUCCESS_PERCENT = "goal_success_percent"
WIDGET_TYPE_GOAL_FAILURE_RISK = "goal_failure_risk"

SUPPORTED_WIDGET_TYPES = {
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
    WIDGET_TYPE_GOAL_PROGRESS,
    WIDGET_TYPE_GOAL_SUMMARY,
    WIDGET_TYPE_GOAL_COMPLETION_PERCENT,
    WIDGET_TYPE_GOAL_SUCCESS_PERCENT,
    WIDGET_TYPE_GOAL_FAILURE_RISK,
}

GOAL_WIDGET_TYPES = {
    WIDGET_TYPE_GOAL_PROGRESS,
    WIDGET_TYPE_GOAL_SUMMARY,
    WIDGET_TYPE_GOAL_COMPLETION_PERCENT,
    WIDGET_TYPE_GOAL_SUCCESS_PERCENT,
    WIDGET_TYPE_GOAL_FAILURE_RISK,
}

METRIC_WIDGET_TYPES = {
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
}

GRID_COLUMN_COUNT = 12
DEFAULT_SUMMARY_WIDGET_WIDTH = 4
DEFAULT_SUMMARY_WIDGET_HEIGHT = 3
DEFAULT_CHART_WIDGET_WIDTH = 6
DEFAULT_CHART_WIDGET_HEIGHT = 4
MAX_WIDGET_HEIGHT = 12


class DashboardError(Exception):
    pass


class DashboardNotFoundError(Exception):
    pass


class DashboardWidgetNotFoundError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_user_timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")


def normalize_recorded_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_name(value: str, *, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if normalized == "":
        raise DashboardError(f"{field_name} is required.")
    if len(normalized) > max_length:
        raise DashboardError(f"{field_name} must be at most {max_length} characters.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized != "" else None


def normalize_widget_type(widget_type: str) -> str:
    normalized = widget_type.strip().lower()
    if normalized not in SUPPORTED_WIDGET_TYPES:
        raise DashboardError("Unsupported widget type.")
    return normalized


def normalize_rolling_window_days(rolling_window_days: int | None) -> int | None:
    if rolling_window_days is None:
        return None
    if rolling_window_days < 1:
        raise DashboardError("Rolling window must be at least 1 day.")
    if rolling_window_days > 3650:
        raise DashboardError("Rolling window must be 3650 days or fewer.")
    return rolling_window_days


def default_widget_dimensions(widget_type: str) -> tuple[int, int]:
    if widget_type in {
        WIDGET_TYPE_METRIC_SUMMARY,
        WIDGET_TYPE_GOAL_SUMMARY,
        WIDGET_TYPE_GOAL_COMPLETION_PERCENT,
        WIDGET_TYPE_GOAL_SUCCESS_PERCENT,
        WIDGET_TYPE_GOAL_FAILURE_RISK,
    }:
        return DEFAULT_SUMMARY_WIDGET_WIDTH, DEFAULT_SUMMARY_WIDGET_HEIGHT
    return DEFAULT_CHART_WIDGET_WIDTH, DEFAULT_CHART_WIDGET_HEIGHT


def normalize_grid_dimension(
    value: int,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> int:
    if value < minimum or value > maximum:
        raise DashboardError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


def normalize_widget_layout(
    *,
    grid_x: int,
    grid_y: int,
    grid_w: int,
    grid_h: int,
) -> tuple[int, int, int, int]:
    normalized_w = normalize_grid_dimension(
        grid_w,
        field_name="Widget width",
        minimum=1,
        maximum=GRID_COLUMN_COUNT,
    )
    normalized_h = normalize_grid_dimension(
        grid_h,
        field_name="Widget height",
        minimum=1,
        maximum=MAX_WIDGET_HEIGHT,
    )
    normalized_x = normalize_grid_dimension(
        grid_x,
        field_name="Widget horizontal position",
        minimum=0,
        maximum=GRID_COLUMN_COUNT - 1,
    )
    normalized_y = normalize_grid_dimension(
        grid_y,
        field_name="Widget vertical position",
        minimum=0,
        maximum=10_000,
    )
    if normalized_x + normalized_w > GRID_COLUMN_COUNT:
        raise DashboardError("Widget layout exceeds dashboard width.")
    return normalized_x, normalized_y, normalized_w, normalized_h


def widgets_overlap(
    *,
    first_x: int,
    first_y: int,
    first_w: int,
    first_h: int,
    second_x: int,
    second_y: int,
    second_w: int,
    second_h: int,
) -> bool:
    return not (
        first_x + first_w <= second_x
        or second_x + second_w <= first_x
        or first_y + first_h <= second_y
        or second_y + second_h <= first_y
    )


def ensure_layout_slot_is_available(
    db: Session,
    *,
    dashboard: Dashboard,
    grid_x: int,
    grid_y: int,
    grid_w: int,
    grid_h: int,
    ignore_widget_id: str | None = None,
) -> None:
    statement = select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard.id)
    widgets = list(db.scalars(statement))
    for existing_widget in widgets:
        if ignore_widget_id is not None and existing_widget.id == ignore_widget_id:
            continue
        if widgets_overlap(
            first_x=grid_x,
            first_y=grid_y,
            first_w=grid_w,
            first_h=grid_h,
            second_x=existing_widget.grid_x,
            second_y=existing_widget.grid_y,
            second_w=existing_widget.grid_w,
            second_h=existing_widget.grid_h,
        ):
            raise DashboardError("Widget layout overlaps another widget.")


def find_first_available_layout_slot(
    db: Session,
    *,
    dashboard: Dashboard,
    grid_w: int,
    grid_h: int,
) -> tuple[int, int]:
    existing_widgets = list(
        db.scalars(select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard.id))
    )
    max_y = max((widget.grid_y + widget.grid_h for widget in existing_widgets), default=0)
    for candidate_y in range(0, max_y + MAX_WIDGET_HEIGHT + 1):
        for candidate_x in range(0, GRID_COLUMN_COUNT - grid_w + 1):
            if any(
                widgets_overlap(
                    first_x=candidate_x,
                    first_y=candidate_y,
                    first_w=grid_w,
                    first_h=grid_h,
                    second_x=existing_widget.grid_x,
                    second_y=existing_widget.grid_y,
                    second_w=existing_widget.grid_w,
                    second_h=existing_widget.grid_h,
                )
                for existing_widget in existing_widgets
            ):
                continue
            return candidate_x, candidate_y
    return 0, max_y


def list_dashboards_for_user(db: Session, user: User) -> list[Dashboard]:
    statement = (
        select(Dashboard)
        .options(
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.metric)
            .selectinload(Metric.entries),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.user),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.exception_dates),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.metric)
            .selectinload(Metric.entries),
        )
        .where(Dashboard.user_id == user.id)
        .order_by(Dashboard.created_at.asc())
    )
    return list(db.scalars(statement))


def get_dashboard_for_user(db: Session, *, user: User, dashboard_id: str) -> Dashboard:
    statement = (
        select(Dashboard)
        .options(
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.metric)
            .selectinload(Metric.entries),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.user),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.exception_dates),
            selectinload(Dashboard.widgets)
            .selectinload(DashboardWidget.goal)
            .selectinload(Goal.metric)
            .selectinload(Metric.entries),
        )
        .where(Dashboard.id == dashboard_id, Dashboard.user_id == user.id)
    )
    dashboard = db.scalar(statement)
    if dashboard is None:
        raise DashboardNotFoundError("Dashboard was not found.")
    return dashboard


def get_dashboard_widget_for_user(
    db: Session, *, user: User, dashboard_id: str, widget_id: str
) -> DashboardWidget:
    statement = (
        select(DashboardWidget)
        .options(
            selectinload(DashboardWidget.metric).selectinload(Metric.entries),
            selectinload(DashboardWidget.goal).selectinload(Goal.user),
            selectinload(DashboardWidget.goal).selectinload(Goal.exception_dates),
            selectinload(DashboardWidget.goal)
            .selectinload(Goal.metric)
            .selectinload(Metric.entries),
        )
        .where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
            DashboardWidget.user_id == user.id,
        )
    )
    widget = db.scalar(statement)
    if widget is None:
        raise DashboardWidgetNotFoundError("Widget was not found.")
    return widget


def create_dashboard(
    db: Session,
    *,
    user: User,
    name: str,
    description: str | None,
    make_default: bool = False,
) -> Dashboard:
    dashboard = Dashboard(
        id=str(uuid4()),
        user_id=user.id,
        name=normalize_name(name, field_name="Dashboard name", max_length=120),
        description=normalize_optional_text(description),
        updated_at=utcnow(),
    )
    db.add(dashboard)
    db.flush()

    existing_dashboard_count = db.scalar(
        select(Dashboard).where(Dashboard.user_id == user.id).limit(2)
    )
    if make_default or user.default_dashboard_id is None or existing_dashboard_count is None:
        user.default_dashboard_id = dashboard.id

    db.flush()
    return get_dashboard_for_user(db, user=user, dashboard_id=dashboard.id)


def update_dashboard(
    db: Session,
    *,
    dashboard: Dashboard,
    user: User,
    name: str | None = None,
    description: str | None = None,
    make_default: bool | None = None,
) -> Dashboard:
    if name is not None:
        dashboard.name = normalize_name(name, field_name="Dashboard name", max_length=120)
    if description is not None:
        dashboard.description = normalize_optional_text(description)
    if make_default is True:
        user.default_dashboard_id = dashboard.id
    dashboard.updated_at = utcnow()
    db.flush()
    return get_dashboard_for_user(db, user=user, dashboard_id=dashboard.id)


def delete_dashboard(db: Session, *, dashboard: Dashboard, user: User) -> None:
    was_default = user.default_dashboard_id == dashboard.id
    dashboard_id = dashboard.id
    db.delete(dashboard)
    db.flush()

    if was_default:
        replacement_dashboard_id = db.scalar(
            select(Dashboard.id)
            .where(Dashboard.user_id == user.id, Dashboard.id != dashboard_id)
            .order_by(Dashboard.created_at.asc())
        )
        user.default_dashboard_id = replacement_dashboard_id
        db.flush()


def create_dashboard_widget(
    db: Session,
    *,
    dashboard: Dashboard,
    user: User,
    title: str,
    widget_type: str,
    metric: Metric | None = None,
    goal: Goal | None = None,
    rolling_window_days: int | None = None,
    grid_x: int | None = None,
    grid_y: int | None = None,
    grid_w: int | None = None,
    grid_h: int | None = None,
) -> DashboardWidget:
    normalized_widget_type = normalize_widget_type(widget_type)
    normalized_window = normalize_rolling_window_days(rolling_window_days)

    if normalized_widget_type in METRIC_WIDGET_TYPES:
        if metric is None or goal is not None:
            raise DashboardError("Metric widgets must reference exactly one metric.")
    elif goal is None or metric is not None:
        raise DashboardError("Goal widgets must reference exactly one goal.")

    if metric is not None and metric.user_id != user.id:
        raise DashboardError("Widgets can only reference your own metrics.")
    if goal is not None and goal.user_id != user.id:
        raise DashboardError("Widgets can only reference your own goals.")
    if goal is not None and goal.target_date is not None:
        normalized_window = None

    default_width, default_height = default_widget_dimensions(normalized_widget_type)
    normalized_width = grid_w if grid_w is not None else default_width
    normalized_height = grid_h if grid_h is not None else default_height

    if grid_x is None or grid_y is None:
        normalized_x, normalized_y = find_first_available_layout_slot(
            db,
            dashboard=dashboard,
            grid_w=normalized_width,
            grid_h=normalized_height,
        )
    else:
        normalized_x = grid_x
        normalized_y = grid_y

    normalized_x, normalized_y, normalized_width, normalized_height = normalize_widget_layout(
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
    )
    ensure_layout_slot_is_available(
        db,
        dashboard=dashboard,
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
    )

    display_order = (
        db.scalar(
            select(DashboardWidget.display_order)
            .where(DashboardWidget.dashboard_id == dashboard.id)
            .order_by(DashboardWidget.display_order.desc())
            .limit(1)
        )
        or 0
    )

    widget = DashboardWidget(
        id=str(uuid4()),
        user_id=user.id,
        dashboard_id=dashboard.id,
        metric_id=metric.id if metric is not None else None,
        goal_id=goal.id if goal is not None else None,
        title=normalize_name(title, field_name="Widget title", max_length=120),
        widget_type=normalized_widget_type,
        rolling_window_days=normalized_window,
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
        display_order=display_order + 1,
        updated_at=utcnow(),
    )
    db.add(widget)
    db.flush()
    return get_dashboard_widget_for_user(
        db,
        user=user,
        dashboard_id=dashboard.id,
        widget_id=widget.id,
    )


def update_dashboard_widget(
    db: Session,
    *,
    dashboard: Dashboard,
    widget: DashboardWidget,
    user: User,
    title: str | None = None,
    rolling_window_days: int | None = None,
    grid_x: int | None = None,
    grid_y: int | None = None,
    grid_w: int | None = None,
    grid_h: int | None = None,
) -> DashboardWidget:
    if title is not None:
        widget.title = normalize_name(title, field_name="Widget title", max_length=120)
    if widget.goal is not None and widget.goal.target_date is not None:
        widget.rolling_window_days = None
    elif rolling_window_days is not None or widget.rolling_window_days is not None:
        widget.rolling_window_days = normalize_rolling_window_days(rolling_window_days)
    if any(value is not None for value in (grid_x, grid_y, grid_w, grid_h)):
        normalized_x, normalized_y, normalized_width, normalized_height = normalize_widget_layout(
            grid_x=grid_x if grid_x is not None else widget.grid_x,
            grid_y=grid_y if grid_y is not None else widget.grid_y,
            grid_w=grid_w if grid_w is not None else widget.grid_w,
            grid_h=grid_h if grid_h is not None else widget.grid_h,
        )
        ensure_layout_slot_is_available(
            db,
            dashboard=dashboard,
            grid_x=normalized_x,
            grid_y=normalized_y,
            grid_w=normalized_width,
            grid_h=normalized_height,
            ignore_widget_id=widget.id,
        )
        widget.grid_x = normalized_x
        widget.grid_y = normalized_y
        widget.grid_w = normalized_width
        widget.grid_h = normalized_height
    widget.updated_at = utcnow()
    db.flush()
    return get_dashboard_widget_for_user(
        db,
        user=user,
        dashboard_id=widget.dashboard_id,
        widget_id=widget.id,
    )


def delete_dashboard_widget(db: Session, *, widget: DashboardWidget) -> None:
    db.delete(widget)
    db.flush()


def sort_metric_entries_ascending(entries: list[MetricEntry]) -> list[MetricEntry]:
    return sorted(entries, key=lambda entry: normalize_recorded_at(entry.recorded_at))


def filter_entries_to_window(
    entries: list[MetricEntry], *, rolling_window_days: int | None
) -> list[MetricEntry]:
    ordered_entries = sort_metric_entries_ascending(entries)
    if rolling_window_days is None or len(ordered_entries) == 0:
        return ordered_entries

    threshold = utcnow() - timedelta(days=rolling_window_days)
    return [
        entry for entry in ordered_entries if normalize_recorded_at(entry.recorded_at) >= threshold
    ]


def metric_entry_numeric_value(metric: Metric, entry: MetricEntry) -> float | int | None:
    if metric.metric_type == "number":
        return entry.number_value
    if entry.date_value is None:
        return None
    return entry.date_value.toordinal()


def goal_target_numeric_value(goal: Goal) -> float | int | None:
    if goal.metric.metric_type == "number":
        return goal.target_value_number
    if goal.target_value_date is None:
        return None
    return goal.target_value_date.toordinal()


def find_goal_baseline_entry(goal: Goal, ordered_entries: list[MetricEntry]) -> MetricEntry | None:
    user_timezone = get_user_timezone(goal.user)
    start_cutoff = datetime.combine(goal.start_date, time.min, tzinfo=user_timezone).astimezone(UTC)
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
    return max(0.0, min(progress_ratio * 100.0, 100.0))


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


def goal_time_completion_percent(goal: Goal, *, as_of: datetime | None = None) -> float | None:
    end_datetime = goal_end_datetime(goal)
    if end_datetime is None:
        return None

    start_datetime = goal_start_datetime(goal)
    comparison_datetime = as_of or utcnow()
    if comparison_datetime <= start_datetime:
        return 0.0
    if comparison_datetime >= end_datetime:
        return 100.0

    total_seconds = (end_datetime - start_datetime).total_seconds()
    if total_seconds <= 0:
        return 100.0

    elapsed_seconds = (comparison_datetime - start_datetime).total_seconds()
    return round(max(0.0, min((elapsed_seconds / total_seconds) * 100.0, 100.0)), 2)


def goal_success_percent(goal: Goal) -> float | None:
    if goal.metric.metric_type == "date":
        return goal_progress_as_of_date(goal)

    points = build_goal_progress_points(goal, rolling_window_days=None)
    if len(points) == 0:
        return None
    return points[-1].progress_percent


def goal_failure_risk_percent(goal: Goal) -> float | None:
    time_completion_percent = goal_time_completion_percent(goal)
    success_percent = goal_success_percent(goal)
    if time_completion_percent is None or success_percent is None:
        return None
    return round(max(0.0, time_completion_percent - success_percent), 2)


def is_target_met(
    *, baseline_value: float | int, target_value: float | int, current_value: float | int
) -> bool:
    if target_value == baseline_value:
        return current_value == target_value
    if target_value > baseline_value:
        return current_value >= target_value
    return current_value <= target_value


@dataclass
class GoalProgressPoint:
    recorded_at: datetime
    number_value: float | int | None
    date_value: date | None
    progress_percent: float


def build_goal_progress_points(
    goal: Goal, *, rolling_window_days: int | None
) -> list[GoalProgressPoint]:
    effective_window = None if goal.target_date is not None else rolling_window_days

    if goal.metric.metric_type == "date":
        date_points = build_goal_date_progress_points(goal)
        if effective_window is not None:
            window_threshold = utcnow() - timedelta(days=effective_window)
            date_points = [
                point
                for point in date_points
                if normalize_recorded_at(point.recorded_at) >= window_threshold
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

    baseline_value = metric_entry_numeric_value(goal.metric, baseline_entry)
    if baseline_value is None:
        return []

    user_timezone = get_user_timezone(goal.user)
    start_cutoff = datetime.combine(goal.start_date, time.min, tzinfo=user_timezone).astimezone(UTC)
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

        current_value = metric_entry_numeric_value(goal.metric, entry)
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


def get_widget_current_progress_percent(widget: DashboardWidget) -> float | None:
    if widget.goal is None:
        return None
    return goal_success_percent(widget.goal)


def get_widget_time_completion_percent(widget: DashboardWidget) -> float | None:
    if widget.goal is None:
        return None
    return goal_time_completion_percent(widget.goal)


def get_widget_failure_risk_percent(widget: DashboardWidget) -> float | None:
    if widget.goal is None:
        return None
    return goal_failure_risk_percent(widget.goal)


def get_widget_target_met(widget: DashboardWidget) -> bool | None:
    if widget.goal is None:
        return None
    if widget.goal.metric.metric_type == "date":
        return goal_target_met(widget.goal)

    target_value = goal_target_numeric_value(widget.goal)
    if target_value is None:
        return None

    ordered_entries = sort_metric_entries_ascending(widget.goal.metric.entries)
    if len(ordered_entries) == 0:
        return None

    baseline_entry = find_goal_baseline_entry(widget.goal, ordered_entries)
    latest_entry = ordered_entries[-1]
    baseline_value = (
        metric_entry_numeric_value(widget.goal.metric, baseline_entry)
        if baseline_entry is not None
        else None
    )
    current_value = metric_entry_numeric_value(widget.goal.metric, latest_entry)
    if baseline_value is None or current_value is None:
        return None

    return is_target_met(
        baseline_value=baseline_value,
        target_value=target_value,
        current_value=current_value,
    )
