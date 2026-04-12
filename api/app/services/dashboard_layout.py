from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dashboard, DashboardWidget

WIDGET_TYPE_METRIC_HISTORY = "metric_history"
WIDGET_TYPE_METRIC_SUMMARY = "metric_summary"
WIDGET_TYPE_DAYS_SINCE = "days_since"
WIDGET_TYPE_GOAL_PROGRESS = "goal_progress"
WIDGET_TYPE_GOAL_SUMMARY = "goal_summary"
WIDGET_TYPE_GOAL_COMPLETION_PERCENT = "goal_completion_percent"
WIDGET_TYPE_GOAL_SUCCESS_PERCENT = "goal_success_percent"
WIDGET_TYPE_GOAL_FAILURE_RISK = "goal_failure_risk"

FORECAST_ALGORITHM_SIMPLE = "simple"
FORECAST_ALGORITHM_WEIGHTED_WEEK_OVER_WEEK = "weighted_week_over_week"
FORECAST_ALGORITHM_WEIGHTED_DAY_OVER_DAY = "weighted_day_over_day"

SUPPORTED_FORECAST_ALGORITHMS = {
    FORECAST_ALGORITHM_SIMPLE,
    FORECAST_ALGORITHM_WEIGHTED_WEEK_OVER_WEEK,
    FORECAST_ALGORITHM_WEIGHTED_DAY_OVER_DAY,
}

SUPPORTED_WIDGET_TYPES = {
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
    WIDGET_TYPE_DAYS_SINCE,
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
    WIDGET_TYPE_DAYS_SINCE,
}

GRID_COLUMN_COUNT = 12
MOBILE_GRID_COLUMN_COUNT = 1
DEFAULT_SUMMARY_WIDGET_WIDTH = 4
DEFAULT_SUMMARY_WIDGET_HEIGHT = 3
DEFAULT_MOBILE_SUMMARY_WIDGET_HEIGHT = 2
DEFAULT_CHART_WIDGET_WIDTH = 6
DEFAULT_CHART_WIDGET_HEIGHT = 4
MAX_WIDGET_HEIGHT = 12
LAYOUT_MODE_DESKTOP = "desktop"
LAYOUT_MODE_MOBILE = "mobile"
SUPPORTED_LAYOUT_MODES = {
    LAYOUT_MODE_DESKTOP,
    LAYOUT_MODE_MOBILE,
}


class DashboardError(Exception):
    pass


def normalize_layout_mode(layout_mode: str | None) -> str:
    if layout_mode is None:
        return LAYOUT_MODE_DESKTOP
    normalized = layout_mode.strip().lower()
    if normalized not in SUPPORTED_LAYOUT_MODES:
        raise DashboardError("Unsupported layout mode.")
    return normalized


def grid_column_count_for_layout_mode(layout_mode: str) -> int:
    return MOBILE_GRID_COLUMN_COUNT if layout_mode == LAYOUT_MODE_MOBILE else GRID_COLUMN_COUNT


def widget_layout_for_mode(
    widget: DashboardWidget,
    *,
    layout_mode: str,
) -> tuple[int, int, int, int]:
    if layout_mode == LAYOUT_MODE_MOBILE:
        return (
            widget.mobile_grid_x,
            widget.mobile_grid_y,
            widget.mobile_grid_w,
            widget.mobile_grid_h,
        )
    return widget.grid_x, widget.grid_y, widget.grid_w, widget.grid_h


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


def normalize_forecast_algorithm(
    *,
    widget_type: str,
    forecast_algorithm: str | None,
) -> str | None:
    if widget_type != WIDGET_TYPE_GOAL_PROGRESS:
        if forecast_algorithm is not None:
            raise DashboardError("Only goal progress widgets can set a forecast algorithm.")
        return None

    if forecast_algorithm is None:
        return FORECAST_ALGORITHM_SIMPLE

    normalized = forecast_algorithm.strip().lower()
    if normalized not in SUPPORTED_FORECAST_ALGORITHMS:
        raise DashboardError("Unsupported forecast algorithm.")
    return normalized


def default_widget_dimensions(widget_type: str) -> tuple[int, int]:
    if widget_type in {
        WIDGET_TYPE_METRIC_SUMMARY,
        WIDGET_TYPE_DAYS_SINCE,
        WIDGET_TYPE_GOAL_SUMMARY,
        WIDGET_TYPE_GOAL_COMPLETION_PERCENT,
        WIDGET_TYPE_GOAL_SUCCESS_PERCENT,
        WIDGET_TYPE_GOAL_FAILURE_RISK,
    }:
        return DEFAULT_SUMMARY_WIDGET_WIDTH, DEFAULT_SUMMARY_WIDGET_HEIGHT
    return DEFAULT_CHART_WIDGET_WIDTH, DEFAULT_CHART_WIDGET_HEIGHT


def default_mobile_widget_height(widget_type: str) -> int:
    if widget_type in {
        WIDGET_TYPE_METRIC_SUMMARY,
        WIDGET_TYPE_DAYS_SINCE,
        WIDGET_TYPE_GOAL_SUMMARY,
        WIDGET_TYPE_GOAL_COMPLETION_PERCENT,
        WIDGET_TYPE_GOAL_SUCCESS_PERCENT,
        WIDGET_TYPE_GOAL_FAILURE_RISK,
    }:
        return DEFAULT_MOBILE_SUMMARY_WIDGET_HEIGHT
    return DEFAULT_CHART_WIDGET_HEIGHT


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
    layout_mode: str = LAYOUT_MODE_DESKTOP,
    grid_x: int,
    grid_y: int,
    grid_w: int,
    grid_h: int,
) -> tuple[int, int, int, int]:
    grid_column_count = grid_column_count_for_layout_mode(layout_mode)
    normalized_w = normalize_grid_dimension(
        grid_w,
        field_name="Widget width",
        minimum=1,
        maximum=grid_column_count,
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
        maximum=grid_column_count - 1,
    )
    normalized_y = normalize_grid_dimension(
        grid_y,
        field_name="Widget vertical position",
        minimum=0,
        maximum=10_000,
    )
    if normalized_x + normalized_w > grid_column_count:
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
    layout_mode: str = LAYOUT_MODE_DESKTOP,
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
        existing_x, existing_y, existing_w, existing_h = widget_layout_for_mode(
            existing_widget,
            layout_mode=layout_mode,
        )
        if widgets_overlap(
            first_x=grid_x,
            first_y=grid_y,
            first_w=grid_w,
            first_h=grid_h,
            second_x=existing_x,
            second_y=existing_y,
            second_w=existing_w,
            second_h=existing_h,
        ):
            raise DashboardError("Widget layout overlaps another widget.")


def find_first_available_layout_slot(
    db: Session,
    *,
    dashboard: Dashboard,
    layout_mode: str = LAYOUT_MODE_DESKTOP,
    grid_w: int,
    grid_h: int,
) -> tuple[int, int]:
    grid_column_count = grid_column_count_for_layout_mode(layout_mode)
    existing_widgets = list(
        db.scalars(select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard.id))
    )
    max_y = max(
        (
            widget_layout_for_mode(widget, layout_mode=layout_mode)[1]
            + widget_layout_for_mode(widget, layout_mode=layout_mode)[3]
            for widget in existing_widgets
        ),
        default=0,
    )
    for candidate_y in range(0, max_y + MAX_WIDGET_HEIGHT + 1):
        for candidate_x in range(0, grid_column_count - grid_w + 1):
            if any(
                widgets_overlap(
                    first_x=candidate_x,
                    first_y=candidate_y,
                    first_w=grid_w,
                    first_h=grid_h,
                    second_x=widget_layout_for_mode(existing_widget, layout_mode=layout_mode)[0],
                    second_y=widget_layout_for_mode(existing_widget, layout_mode=layout_mode)[1],
                    second_w=widget_layout_for_mode(existing_widget, layout_mode=layout_mode)[2],
                    second_h=widget_layout_for_mode(existing_widget, layout_mode=layout_mode)[3],
                )
                for existing_widget in existing_widgets
            ):
                continue
            return candidate_x, candidate_y
    return 0, max_y
