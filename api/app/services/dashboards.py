from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Dashboard, DashboardWidget, Goal, Metric, MetricEntry, User

WIDGET_TYPE_METRIC_HISTORY = "metric_history"
WIDGET_TYPE_METRIC_SUMMARY = "metric_summary"
WIDGET_TYPE_GOAL_PROGRESS = "goal_progress"
WIDGET_TYPE_GOAL_SUMMARY = "goal_summary"

SUPPORTED_WIDGET_TYPES = {
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
    WIDGET_TYPE_GOAL_PROGRESS,
    WIDGET_TYPE_GOAL_SUMMARY,
}

GOAL_WIDGET_TYPES = {
    WIDGET_TYPE_GOAL_PROGRESS,
    WIDGET_TYPE_GOAL_SUMMARY,
}

METRIC_WIDGET_TYPES = {
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
}


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
    widget: DashboardWidget,
    user: User,
    title: str | None = None,
    rolling_window_days: int | None = None,
) -> DashboardWidget:
    if title is not None:
        widget.title = normalize_name(title, field_name="Widget title", max_length=120)
    if rolling_window_days is not None or widget.rolling_window_days is not None:
        widget.rolling_window_days = normalize_rolling_window_days(rolling_window_days)
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
    entry: MetricEntry
    progress_percent: float


def build_goal_progress_points(
    goal: Goal, *, rolling_window_days: int | None
) -> list[GoalProgressPoint]:
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
    window_threshold = (
        utcnow() - timedelta(days=rolling_window_days) if rolling_window_days is not None else None
    )

    points: list[GoalProgressPoint] = []
    for entry in ordered_entries:
        recorded_at = normalize_recorded_at(entry.recorded_at)
        if recorded_at < start_cutoff:
            continue
        if window_threshold is not None and recorded_at < window_threshold:
            continue

        current_value = metric_entry_numeric_value(goal.metric, entry)
        if current_value is None:
            continue

        points.append(
            GoalProgressPoint(
                entry=entry,
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
    points = build_goal_progress_points(
        widget.goal,
        rolling_window_days=widget.rolling_window_days,
    )
    if len(points) == 0:
        return None
    return points[-1].progress_percent


def get_widget_target_met(widget: DashboardWidget) -> bool | None:
    if widget.goal is None:
        return None

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
