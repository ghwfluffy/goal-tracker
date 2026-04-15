from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Dashboard,
    DashboardWidget,
    DashboardWidgetGoal,
    Goal,
    Metric,
    MetricEntry,
    User,
)
from app.services.dashboard_layout import (
    LAYOUT_MODE_DESKTOP,
    LAYOUT_MODE_MOBILE,
    METRIC_WIDGET_TYPES,
    WIDGET_GOAL_SCOPE_ALL,
    WIDGET_GOAL_SCOPE_SELECTED,
    WIDGET_TYPE_DAYS_SINCE,
    WIDGET_TYPE_GOAL_CALENDAR,
    DashboardError,
    default_mobile_widget_height,
    default_widget_dimensions,
    ensure_layout_slot_is_available,
    find_first_available_layout_slot,
    normalize_calendar_period,
    normalize_forecast_algorithm,
    normalize_layout_mode,
    normalize_name,
    normalize_optional_text,
    normalize_rolling_window_days,
    normalize_widget_goal_scope,
    normalize_widget_layout,
    normalize_widget_type,
)
from app.services.goal_progress import (
    normalize_recorded_at,
    sort_metric_entries_ascending,
    utcnow,
)


class DashboardNotFoundError(Exception):
    pass


class DashboardWidgetNotFoundError(Exception):
    pass


def restack_mobile_layouts(
    db: Session,
    *,
    dashboard: Dashboard,
    priority_widget_id: str | None = None,
) -> None:
    widgets = list(db.scalars(select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard.id)))
    widgets.sort(
        key=lambda widget: (
            widget.mobile_grid_y,
            0 if priority_widget_id is not None and widget.id == priority_widget_id else 1,
            widget.display_order,
        )
    )
    next_y = 0
    for widget in widgets:
        widget.mobile_grid_x = 0
        widget.mobile_grid_w = 1
        widget.mobile_grid_y = next_y
        next_y += widget.mobile_grid_h


def _dashboard_loading_options() -> tuple[Any, ...]:
    return (
        selectinload(Dashboard.widgets).selectinload(DashboardWidget.metric).selectinload(Metric.entries),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.user),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.exception_dates),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.checklist_items),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.entries),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.notifications),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.exception_dates),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.checklist_items),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.metric)
        .selectinload(Metric.entries),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.metric)
        .selectinload(Metric.notifications),
        selectinload(Dashboard.widgets).selectinload(DashboardWidget.goal).selectinload(Goal.user),
        selectinload(Dashboard.widgets).selectinload(DashboardWidget.goal).selectinload(Goal.exception_dates),
        selectinload(Dashboard.widgets).selectinload(DashboardWidget.goal).selectinload(Goal.checklist_items),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.entries),
        selectinload(Dashboard.widgets)
        .selectinload(DashboardWidget.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.notifications),
    )


def _widget_loading_options() -> tuple[Any, ...]:
    return (
        selectinload(DashboardWidget.metric).selectinload(Metric.entries),
        selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.user),
        selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.exception_dates),
        selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.checklist_items),
        selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.entries),
        selectinload(DashboardWidget.goal_links)
        .selectinload(DashboardWidgetGoal.goal)
        .selectinload(Goal.metric)
        .selectinload(Metric.notifications),
        selectinload(DashboardWidget.user).selectinload(User.goals).selectinload(Goal.exception_dates),
        selectinload(DashboardWidget.user).selectinload(User.goals).selectinload(Goal.checklist_items),
        selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.metric)
        .selectinload(Metric.entries),
        selectinload(DashboardWidget.user)
        .selectinload(User.goals)
        .selectinload(Goal.metric)
        .selectinload(Metric.notifications),
        selectinload(DashboardWidget.goal).selectinload(Goal.user),
        selectinload(DashboardWidget.goal).selectinload(Goal.exception_dates),
        selectinload(DashboardWidget.goal).selectinload(Goal.checklist_items),
        selectinload(DashboardWidget.goal).selectinload(Goal.metric).selectinload(Metric.entries),
        selectinload(DashboardWidget.goal).selectinload(Goal.metric).selectinload(Metric.notifications),
    )


def list_dashboards_for_user(db: Session, user: User) -> list[Dashboard]:
    statement = (
        select(Dashboard)
        .options(*_dashboard_loading_options())
        .where(Dashboard.user_id == user.id)
        .order_by(Dashboard.created_at.asc())
    )
    return list(db.scalars(statement))


def get_dashboard_for_user(db: Session, *, user: User, dashboard_id: str) -> Dashboard:
    statement = (
        select(Dashboard)
        .options(*_dashboard_loading_options())
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
        .options(*_widget_loading_options())
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

    existing_dashboard_count = db.scalar(select(Dashboard).where(Dashboard.user_id == user.id).limit(2))
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
    goals: list[Goal] | None = None,
    goal_scope: str | None = None,
    calendar_period: str | None = None,
    rolling_window_days: int | None = None,
    forecast_algorithm: str | None = None,
    grid_x: int | None = None,
    grid_y: int | None = None,
    grid_w: int | None = None,
    grid_h: int | None = None,
) -> DashboardWidget:
    normalized_widget_type = normalize_widget_type(widget_type)
    normalized_goal_scope = normalize_widget_goal_scope(goal_scope)
    normalized_calendar_period = normalize_calendar_period(calendar_period)
    normalized_window = normalize_rolling_window_days(rolling_window_days)
    normalized_forecast_algorithm = normalize_forecast_algorithm(
        widget_type=normalized_widget_type,
        forecast_algorithm=forecast_algorithm,
    )

    selected_goals = goals or []

    if normalized_widget_type == WIDGET_TYPE_GOAL_CALENDAR:
        if metric is not None or goal is not None:
            raise DashboardError("Goal calendar widgets cannot reference metric_id or goal_id.")
        if normalized_goal_scope is None:
            raise DashboardError("Goal calendar widgets require a goal scope.")
        if normalized_goal_scope == WIDGET_GOAL_SCOPE_SELECTED and len(selected_goals) == 0:
            raise DashboardError("Goal calendar widgets require at least one selected goal.")
        if normalized_goal_scope == WIDGET_GOAL_SCOPE_ALL and len(selected_goals) > 0:
            raise DashboardError("All-goals calendar widgets cannot set selected goals.")
        if normalized_calendar_period is None:
            raise DashboardError("Goal calendar widgets require a calendar period.")
    elif normalized_widget_type in METRIC_WIDGET_TYPES:
        if metric is None or goal is not None:
            raise DashboardError("Metric widgets must reference exactly one metric.")
    elif goal is None or metric is not None:
        raise DashboardError("Goal widgets must reference exactly one goal.")

    if metric is not None and metric.user_id != user.id:
        raise DashboardError("Widgets can only reference your own metrics.")
    if goal is not None and goal.user_id != user.id:
        raise DashboardError("Widgets can only reference your own goals.")
    for selected_goal in selected_goals:
        if selected_goal.user_id != user.id:
            raise DashboardError("Widgets can only reference your own goals.")
    if normalized_widget_type == WIDGET_TYPE_DAYS_SINCE and (metric is None or metric.metric_type != "date"):
        raise DashboardError("Days since widgets require a date metric.")
    if normalized_widget_type == WIDGET_TYPE_GOAL_CALENDAR:
        for selected_goal in selected_goals:
            if selected_goal.metric is None and selected_goal.goal_type != "checklist":
                raise DashboardError("Calendar widgets require supported goals.")
    if goal is not None and goal.target_date is not None:
        normalized_window = None
    if normalized_widget_type == WIDGET_TYPE_GOAL_CALENDAR:
        normalized_window = None
        normalized_forecast_algorithm = None

    default_width, default_height = default_widget_dimensions(normalized_widget_type)
    normalized_width = grid_w if grid_w is not None else default_width
    normalized_height = grid_h if grid_h is not None else default_height

    if grid_x is None or grid_y is None:
        normalized_x, normalized_y = find_first_available_layout_slot(
            db,
            dashboard=dashboard,
            layout_mode=LAYOUT_MODE_DESKTOP,
            grid_w=normalized_width,
            grid_h=normalized_height,
        )
    else:
        normalized_x = grid_x
        normalized_y = grid_y

    normalized_x, normalized_y, normalized_width, normalized_height = normalize_widget_layout(
        layout_mode=LAYOUT_MODE_DESKTOP,
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
    )
    ensure_layout_slot_is_available(
        db,
        dashboard=dashboard,
        layout_mode=LAYOUT_MODE_DESKTOP,
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
    )

    mobile_width = 1
    mobile_height = default_mobile_widget_height(normalized_widget_type)
    mobile_x, mobile_y = find_first_available_layout_slot(
        db,
        dashboard=dashboard,
        layout_mode=LAYOUT_MODE_MOBILE,
        grid_w=mobile_width,
        grid_h=mobile_height,
    )
    mobile_x, mobile_y, mobile_width, mobile_height = normalize_widget_layout(
        layout_mode=LAYOUT_MODE_MOBILE,
        grid_x=mobile_x,
        grid_y=mobile_y,
        grid_w=mobile_width,
        grid_h=mobile_height,
    )
    ensure_layout_slot_is_available(
        db,
        dashboard=dashboard,
        layout_mode=LAYOUT_MODE_MOBILE,
        grid_x=mobile_x,
        grid_y=mobile_y,
        grid_w=mobile_width,
        grid_h=mobile_height,
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
        goal_scope=normalized_goal_scope,
        calendar_period=normalized_calendar_period,
        rolling_window_days=normalized_window,
        forecast_algorithm=normalized_forecast_algorithm,
        grid_x=normalized_x,
        grid_y=normalized_y,
        grid_w=normalized_width,
        grid_h=normalized_height,
        mobile_grid_x=mobile_x,
        mobile_grid_y=mobile_y,
        mobile_grid_w=mobile_width,
        mobile_grid_h=mobile_height,
        display_order=display_order + 1,
        updated_at=utcnow(),
    )
    db.add(widget)
    db.flush()

    if (
        normalized_widget_type == WIDGET_TYPE_GOAL_CALENDAR
        and normalized_goal_scope == WIDGET_GOAL_SCOPE_SELECTED
    ):
        for display_order, selected_goal in enumerate(selected_goals):
            db.add(
                DashboardWidgetGoal(
                    id=str(uuid4()),
                    widget_id=widget.id,
                    goal_id=selected_goal.id,
                    display_order=display_order,
                )
            )

    restack_mobile_layouts(db, dashboard=dashboard)
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
    forecast_algorithm: str | None = None,
    calendar_period: str | None = None,
    layout_mode: str | None = None,
    grid_x: int | None = None,
    grid_y: int | None = None,
    grid_w: int | None = None,
    grid_h: int | None = None,
) -> DashboardWidget:
    normalized_layout_mode = normalize_layout_mode(layout_mode)
    if title is not None:
        widget.title = normalize_name(title, field_name="Widget title", max_length=120)
    if forecast_algorithm is not None or widget.forecast_algorithm is not None:
        if widget.widget_type == WIDGET_TYPE_GOAL_CALENDAR and forecast_algorithm is not None:
            raise DashboardError("Goal calendar widgets do not support forecast algorithms.")
        widget.forecast_algorithm = normalize_forecast_algorithm(
            widget_type=widget.widget_type,
            forecast_algorithm=forecast_algorithm,
        )
    if widget.goal is not None and widget.goal.target_date is not None:
        widget.rolling_window_days = None
    elif widget.widget_type == WIDGET_TYPE_GOAL_CALENDAR:
        if rolling_window_days is not None:
            raise DashboardError("Goal calendar widgets do not support rolling windows.")
        widget.rolling_window_days = None
    elif rolling_window_days is not None or widget.rolling_window_days is not None:
        widget.rolling_window_days = normalize_rolling_window_days(rolling_window_days)
    if calendar_period is not None:
        if widget.widget_type != WIDGET_TYPE_GOAL_CALENDAR:
            raise DashboardError("Only goal calendar widgets can set a calendar period.")
        widget.calendar_period = normalize_calendar_period(calendar_period)
    if any(value is not None for value in (grid_x, grid_y, grid_w, grid_h)):
        if normalized_layout_mode == LAYOUT_MODE_MOBILE:
            _, normalized_y, _, normalized_height = normalize_widget_layout(
                layout_mode=normalized_layout_mode,
                grid_x=0,
                grid_y=grid_y if grid_y is not None else widget.mobile_grid_y,
                grid_w=1,
                grid_h=grid_h if grid_h is not None else widget.mobile_grid_h,
            )
            widget.mobile_grid_x = 0
            widget.mobile_grid_y = normalized_y
            widget.mobile_grid_w = 1
            widget.mobile_grid_h = normalized_height
            restack_mobile_layouts(db, dashboard=dashboard, priority_widget_id=widget.id)
        else:
            normalized_x, normalized_y, normalized_width, normalized_height = normalize_widget_layout(
                layout_mode=normalized_layout_mode,
                grid_x=grid_x if grid_x is not None else widget.grid_x,
                grid_y=grid_y if grid_y is not None else widget.grid_y,
                grid_w=grid_w if grid_w is not None else widget.grid_w,
                grid_h=grid_h if grid_h is not None else widget.grid_h,
            )
            ensure_layout_slot_is_available(
                db,
                dashboard=dashboard,
                layout_mode=normalized_layout_mode,
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


def filter_entries_to_window(
    entries: list[MetricEntry], *, rolling_window_days: int | None
) -> list[MetricEntry]:
    ordered_entries = sort_metric_entries_ascending(entries)
    if rolling_window_days is None or len(ordered_entries) == 0:
        return ordered_entries

    threshold = utcnow() - timedelta(days=rolling_window_days)
    return [entry for entry in ordered_entries if normalize_recorded_at(entry.recorded_at) >= threshold]
