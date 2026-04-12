from __future__ import annotations

import json
from datetime import UTC, date, datetime
from functools import lru_cache
from html import escape
from io import BytesIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.api.schemas.dashboards import (
    DashboardSummary,
    GoalReferenceSummary,
    MetricEntrySummary,
    MetricReferenceSummary,
    WidgetSummary,
)

PREVIEW_WIDTH = 1200
PREVIEW_HEIGHT = 630

COLOR_BG = (7, 10, 18, 255)
COLOR_PANEL = (15, 19, 30, 232)
COLOR_PANEL_BORDER = (255, 255, 255, 32)
COLOR_TEXT = (235, 240, 255, 255)
COLOR_MUTED = (170, 178, 195, 255)
COLOR_GRID = (255, 255, 255, 24)
COLOR_GREEN = (33, 255, 106, 255)
COLOR_BLUE = (47, 123, 255, 255)
COLOR_RED = (255, 59, 59, 255)
COLOR_WHITE = (248, 250, 255, 255)

WIDGET_TYPE_LABELS: dict[str, str] = {
    "metric_history": "Metric history",
    "metric_summary": "Metric summary",
    "days_since": "Days since",
    "goal_progress": "Goal progress",
    "goal_checklist": "Checklist",
    "goal_summary": "Goal summary",
    "goal_completion_percent": "Goal completion",
    "goal_success_percent": "Goal success",
    "goal_failure_risk": "Failure risk",
}


@lru_cache(maxsize=16)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    )
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _format_calendar_date(value: date) -> str:
    return value.strftime("%b %d, %Y").replace(" 0", " ")


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_recorded_at(value: str) -> str:
    return _format_calendar_date(_parse_iso_datetime(value).date())


def _safe_zoneinfo(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")


def _current_date_in_timezone(timezone: str) -> date:
    return datetime.now(_safe_zoneinfo(timezone)).date()


def _format_number(value: float, decimal_places: int | None, unit_label: str | None) -> str:
    formatted = f"{value:.{decimal_places or 0}f}"
    return f"{formatted} {unit_label}" if unit_label else formatted


def _format_metric_entry(metric: MetricReferenceSummary, entry: MetricEntrySummary | None) -> str:
    if entry is None:
        return "No value"
    if metric.metric_type == "number":
        if entry.number_value is None:
            return "No value"
        return _format_number(entry.number_value, metric.decimal_places, metric.unit_label)
    if entry.date_value is None:
        return "No value"
    return _format_calendar_date(date.fromisoformat(entry.date_value))


def _format_goal_target(goal: GoalReferenceSummary) -> str | None:
    if goal.metric is None:
        return None
    if goal.metric.metric_type == "number" and goal.target_value_number is not None:
        return _format_number(goal.target_value_number, goal.metric.decimal_places, goal.metric.unit_label)
    if goal.metric.metric_type == "date" and goal.target_value_date is not None:
        return _format_calendar_date(date.fromisoformat(goal.target_value_date))
    return None


def widget_type_label(widget_type: str) -> str:
    return WIDGET_TYPE_LABELS.get(widget_type, "Shared widget")


def widget_primary_value_text(widget: WidgetSummary, *, profile_timezone: str) -> str:
    if widget.widget_type in {"metric_history", "metric_summary"} and widget.metric is not None:
        return _format_metric_entry(widget.metric, widget.metric.latest_entry)

    if widget.widget_type == "days_since" and widget.metric is not None:
        latest_entry = widget.metric.latest_entry
        if latest_entry is None or latest_entry.date_value is None:
            return "No value"
        latest_date = date.fromisoformat(latest_entry.date_value)
        days_since = (_current_date_in_timezone(profile_timezone) - latest_date).days
        if days_since < 0:
            days_since = 0
        return "1 day" if days_since == 1 else f"{days_since} days"

    if widget.widget_type == "goal_completion_percent":
        return (
            "No value"
            if widget.time_completion_percent is None
            else f"{round(widget.time_completion_percent)}%"
        )

    if widget.widget_type == "goal_failure_risk":
        return "No value" if widget.failure_risk_percent is None else f"{round(widget.failure_risk_percent)}%"

    if widget.widget_type == "goal_checklist" and widget.goal is not None:
        return f"{widget.goal.checklist_completed_count}/{widget.goal.checklist_total_count} done"

    if (
        widget.widget_type == "goal_summary"
        and widget.goal is not None
        and widget.goal.goal_type == "checklist"
    ):
        return f"{widget.goal.checklist_completed_count}/{widget.goal.checklist_total_count} done"

    if widget.widget_type in {"goal_progress", "goal_summary", "goal_success_percent"}:
        return (
            "No value"
            if widget.current_progress_percent is None
            else f"{round(widget.current_progress_percent)}%"
        )

    return "No value"


def widget_subject_text(widget: WidgetSummary) -> str:
    if widget.metric is not None:
        return f"Metric · {widget.metric.name}"
    if widget.goal is not None:
        return f"Goal · {widget.goal.title}"
    return "Shared widget"


def widget_detail_text(widget: WidgetSummary, *, profile_timezone: str) -> str:
    if widget.metric is not None:
        latest_entry = widget.metric.latest_entry
        if (
            widget.widget_type == "days_since"
            and latest_entry is not None
            and latest_entry.date_value is not None
        ):
            return f"Since {_format_calendar_date(date.fromisoformat(latest_entry.date_value))}"
        if latest_entry is not None:
            return f"Latest {_format_recorded_at(latest_entry.recorded_at)}"
        return "No recorded entries yet."

    if widget.goal is not None:
        parts: list[str] = []
        if widget.goal.metric is not None:
            latest_value = _format_metric_entry(widget.goal.metric, widget.goal.metric.latest_entry)
            if latest_value != "No value":
                parts.append(f"Latest {latest_value}")
        elif widget.goal.goal_type == "checklist":
            parts.append(
                f"{widget.goal.checklist_completed_count} of {widget.goal.checklist_total_count} completed"
            )
        target_value = _format_goal_target(widget.goal)
        if target_value is not None:
            parts.append(f"Target {target_value}")
        if widget.goal.target_date is not None:
            parts.append(f"By {_format_calendar_date(date.fromisoformat(widget.goal.target_date))}")
        return " · ".join(parts) if parts else "Goal progress is shared read-only."

    return "Shared read-only."


def widget_og_description(widget: WidgetSummary, *, profile_timezone: str) -> str:
    return (
        f"{widget_type_label(widget.widget_type)} · "
        f"{widget_primary_value_text(widget, profile_timezone=profile_timezone)}"
    )


def widget_og_title(widget: WidgetSummary, *, profile_timezone: str) -> str:
    if widget.goal is not None:
        progress_label = _widget_progress_label(widget)
        return f"{widget.title} - {progress_label}" if progress_label is not None else widget.title
    return f"{widget.title} - {widget_primary_value_text(widget, profile_timezone=profile_timezone)}"


def dashboard_og_description(dashboard: DashboardSummary, *, profile_timezone: str) -> str:
    if len(dashboard.widgets) == 0:
        return "Shared dashboard"
    highlights = ", ".join(
        f"{widget.title}: {widget_primary_value_text(widget, profile_timezone=profile_timezone)}"
        for widget in dashboard.widgets[:2]
    )
    return f"Shared dashboard · {highlights}"


def _widget_chart_mode(widget: WidgetSummary) -> str:
    if widget.metric is not None:
        return "metric_date" if widget.metric.metric_type == "date" else "metric_number"

    if widget.goal is not None:
        goal_metric = widget.goal.metric
        if goal_metric is None:
            return "progress_percent"
        has_date_values = any(point.date_value is not None for point in widget.series)
        has_number_values = any(point.number_value is not None for point in widget.series)
        if goal_metric.metric_type == "date" and has_date_values:
            return "metric_date"
        if goal_metric.metric_type == "number" and has_number_values:
            return "metric_number"
        return "progress_percent"

    return "metric_number"


def _widget_chart_values(widget: WidgetSummary) -> list[float]:
    values: list[float] = []
    chart_mode = _widget_chart_mode(widget)

    for point in widget.series:
        if chart_mode == "progress_percent" and point.progress_percent is not None:
            values.append(float(point.progress_percent))
            continue
        if chart_mode == "metric_date" and point.date_value is not None:
            values.append(float(date.fromisoformat(point.date_value).toordinal()))
            continue
        if chart_mode == "metric_number" and point.number_value is not None:
            values.append(float(point.number_value))

    return values


def _widget_chart_points(widget: WidgetSummary) -> list[tuple[datetime, float]]:
    points: list[tuple[datetime, float]] = []
    chart_mode = _widget_chart_mode(widget)

    for point in widget.series:
        value: float | None = None
        if chart_mode == "progress_percent" and point.progress_percent is not None:
            value = float(point.progress_percent)
        elif chart_mode == "metric_date" and point.date_value is not None:
            value = float(date.fromisoformat(point.date_value).toordinal())
        elif chart_mode == "metric_number" and point.number_value is not None:
            value = float(point.number_value)

        if value is None:
            continue

        points.append((_parse_iso_datetime(point.recorded_at), value))

    return points


def _widget_chart_target(widget: WidgetSummary) -> float | None:
    if widget.goal is None:
        return None

    chart_mode = _widget_chart_mode(widget)
    if chart_mode == "progress_percent":
        return 100.0
    if chart_mode == "metric_number" and widget.goal.target_value_number is not None:
        return float(widget.goal.target_value_number)
    if chart_mode == "metric_date" and widget.goal.target_value_date is not None:
        return float(date.fromisoformat(widget.goal.target_value_date).toordinal())
    return None


def _widget_accent_color(widget: WidgetSummary) -> tuple[int, int, int, int]:
    if widget.widget_type == "goal_failure_risk":
        return COLOR_RED
    if widget.widget_type == "goal_completion_percent":
        return COLOR_BLUE
    if widget.widget_type == "days_since":
        return COLOR_BLUE
    return COLOR_GREEN


def _widget_progress_label(widget: WidgetSummary) -> str | None:
    if widget.goal is not None and widget.time_completion_percent is not None:
        return f"{round(widget.time_completion_percent)}%"
    if widget.current_progress_percent is not None:
        return f"{round(widget.current_progress_percent)}%"
    if widget.time_completion_percent is not None:
        return f"{round(widget.time_completion_percent)}%"
    return None


def _sample_values(values: list[float], *, max_points: int) -> list[float]:
    if len(values) <= max_points:
        return values
    if max_points <= 1:
        return [values[-1]]

    sampled = [values[0]]
    last_index = len(values) - 1
    for position in range(1, max_points - 1):
        index = round(position * last_index / (max_points - 1))
        sampled.append(values[index])
    sampled.append(values[-1])
    return sampled


def _sample_series_points(
    values: list[tuple[datetime, float]],
    *,
    max_points: int,
) -> list[tuple[datetime, float]]:
    if len(values) <= max_points:
        return values
    if max_points <= 1:
        return [values[-1]]

    sampled = [values[0]]
    last_index = len(values) - 1
    for position in range(1, max_points - 1):
        index = round(position * last_index / (max_points - 1))
        sampled.append(values[index])
    sampled.append(values[-1])
    return sampled


def _line_points(
    values: list[float],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    target_value: float | None = None,
) -> list[tuple[float, float]]:
    sampled_values = _sample_values(values, max_points=48)
    if len(sampled_values) == 1:
        sampled_values = [sampled_values[0], sampled_values[0]]

    minimum = min(sampled_values + ([target_value] if target_value is not None else []))
    maximum = max(sampled_values + ([target_value] if target_value is not None else []))
    if minimum == maximum:
        minimum -= 1
        maximum += 1

    points: list[tuple[float, float]] = []
    for index, value in enumerate(sampled_values):
        progress = 0 if len(sampled_values) == 1 else index / (len(sampled_values) - 1)
        px = x + progress * width
        py = y + height - ((value - minimum) / (maximum - minimum)) * height
        points.append((px, py))
    return points


def _normalize_chart_bounds(values: list[float], *, target_value: float | None = None) -> tuple[float, float]:
    comparison_values = [*values]
    if target_value is not None:
        comparison_values.append(target_value)

    minimum = min(comparison_values)
    maximum = max(comparison_values)
    if minimum == maximum:
        minimum -= 1
        maximum += 1
    return minimum, maximum


def _target_y_position(
    values: list[float],
    *,
    y: int,
    height: int,
    target_value: float | None,
) -> float | None:
    if target_value is None:
        return None
    sampled_values = _sample_values(values, max_points=48)
    minimum = min(sampled_values + [target_value])
    maximum = max(sampled_values + [target_value])
    if minimum == maximum:
        minimum -= 1
        maximum += 1
    return y + height - ((target_value - minimum) / (maximum - minimum)) * height


def _format_chart_value(widget: WidgetSummary, value: float) -> str:
    chart_mode = _widget_chart_mode(widget)
    if chart_mode == "progress_percent":
        return f"{round(value)}%"
    if chart_mode == "metric_date":
        return _format_calendar_date(date.fromordinal(round(value)))
    if widget.metric is not None:
        return _format_number(value, widget.metric.decimal_places, widget.metric.unit_label)
    if widget.goal is not None:
        if widget.goal.metric is None:
            return f"{round(value)}%"
        return _format_number(value, widget.goal.metric.decimal_places, widget.goal.metric.unit_label)
    return f"{round(value)}"


def _chart_summary_text(widget: WidgetSummary, *, profile_timezone: str) -> str:
    if widget.metric is not None and widget.metric.latest_entry is not None:
        return f"Latest {_format_recorded_at(widget.metric.latest_entry.recorded_at)}"
    if widget.goal is not None:
        if widget.goal.target_date is not None:
            return f"Target {_format_calendar_date(date.fromisoformat(widget.goal.target_date))}"
        return widget_detail_text(widget, profile_timezone=profile_timezone)
    return widget_detail_text(widget, profile_timezone=profile_timezone)


def _forecast_value_at_timestamp(
    timestamp: datetime,
    *,
    last_actual_timestamp: datetime,
    last_actual_value: float,
    target_timestamp: datetime,
    target_value: float,
) -> float:
    if target_timestamp <= last_actual_timestamp:
        return target_value

    timestamp_seconds = timestamp.timestamp()
    start_seconds = last_actual_timestamp.timestamp()
    target_seconds = target_timestamp.timestamp()
    progress_ratio = (timestamp_seconds - start_seconds) / (target_seconds - start_seconds)
    projected_value = last_actual_value + (target_value - last_actual_value) * progress_ratio
    lower_bound = min(last_actual_value, target_value)
    upper_bound = max(last_actual_value, target_value)
    return max(lower_bound, min(projected_value, upper_bound))


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int | None = None,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current_line = candidate
            continue
        lines.append(current_line)
        current_line = word
        if max_lines is not None and len(lines) >= max_lines - 1:
            break

    lines.append(current_line)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]

    if max_lines is not None and len(words) > 1:
        visible_text = " ".join(lines)
        if visible_text != text and lines:
            while draw.textlength(f"{lines[-1]}…", font=font) > max_width and len(lines[-1]) > 1:
                lines[-1] = lines[-1][:-1]
            lines[-1] = f"{lines[-1]}…"

    return lines


def _draw_glows(image: Image.Image) -> None:
    glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.ellipse((-120, -80, 360, 300), fill=(33, 255, 106, 55))
    glow_draw.ellipse((780, 20, 1220, 360), fill=(47, 123, 255, 52))
    blurred = glow_layer.filter(ImageFilter.GaussianBlur(70))
    image.alpha_composite(blurred)


def _render_widget_preview_image(
    widget: WidgetSummary,
    *,
    dashboard_name: str | None,
    profile_timezone: str,
) -> Image.Image:
    del dashboard_name
    image = Image.new("RGBA", (PREVIEW_WIDTH, PREVIEW_HEIGHT), COLOR_BG)
    _draw_glows(image)
    draw = ImageDraw.Draw(image)

    panel_bounds = (44, 44, PREVIEW_WIDTH - 44, PREVIEW_HEIGHT - 44)
    draw.rounded_rectangle(panel_bounds, radius=28, fill=COLOR_PANEL, outline=COLOR_PANEL_BORDER, width=2)

    metric_font = _font(54, bold=True)
    metric_label_font = _font(21, bold=True)
    point_value_font = _font(30, bold=True)

    progress_label = _widget_progress_label(widget)
    if progress_label is not None:
        progress_width = draw.textlength(progress_label, font=metric_font)
        progress_x = PREVIEW_WIDTH - 84 - progress_width
        draw.text((progress_x, 90), progress_label, font=metric_font, fill=COLOR_TEXT)
        progress_caption_width = draw.textlength("PROGRESS", font=metric_label_font)
        draw.text(
            (PREVIEW_WIDTH - 84 - progress_caption_width, 136),
            "PROGRESS",
            font=metric_label_font,
            fill=COLOR_MUTED,
        )

    chart_x = 82
    chart_y = 110
    chart_width = PREVIEW_WIDTH - 164
    chart_height = 438
    chart_bounds = (chart_x, chart_y, chart_x + chart_width, chart_y + chart_height)
    draw.rounded_rectangle(
        chart_bounds,
        radius=22,
        fill=(9, 13, 24, 255),
        outline=(255, 255, 255, 14),
        width=2,
    )

    plot_left = chart_x + 28
    plot_top = chart_y + 26
    plot_width = chart_width - 56
    plot_height = chart_height - 52

    chart_values = _widget_chart_values(widget)
    actual_points = _widget_chart_points(widget)
    target_value = _widget_chart_target(widget)
    for row_index in range(4):
        row_y = plot_top + row_index * (plot_height / 3)
        draw.line((plot_left, row_y, plot_left + plot_width, row_y), fill=(255, 255, 255, 18), width=1)

    if len(chart_values) >= 1 and len(actual_points) >= 1:
        now_timestamp = datetime.now(UTC)
        target_timestamp: datetime | None = None
        if widget.goal is not None and widget.goal.target_date is not None:
            target_timestamp = datetime.combine(
                date.fromisoformat(widget.goal.target_date),
                datetime.max.time(),
                tzinfo=UTC,
            )

        comparison_values = [*chart_values]
        if target_value is not None:
            comparison_values.append(target_value)

        actual_timestamps = [point[0].timestamp() for point in actual_points]
        if target_timestamp is not None:
            actual_timestamps.append(target_timestamp.timestamp())
        if now_timestamp > actual_points[-1][0]:
            actual_timestamps.append(now_timestamp.timestamp())

        min_timestamp = min(actual_timestamps)
        max_timestamp = max(actual_timestamps)
        if min_timestamp == max_timestamp:
            min_timestamp -= 1
            max_timestamp += 1

        minimum, maximum = _normalize_chart_bounds(chart_values, target_value=target_value)

        def chart_x_for(timestamp: datetime) -> float:
            return (
                plot_left
                + ((timestamp.timestamp() - min_timestamp) / (max_timestamp - min_timestamp)) * plot_width
            )

        def chart_y_for(value: float) -> float:
            return plot_top + plot_height - ((value - minimum) / (maximum - minimum)) * plot_height

        actual_line_points = [(chart_x_for(ts), chart_y_for(value)) for ts, value in actual_points]
        if len(actual_line_points) >= 2:
            draw.line(actual_line_points, fill=COLOR_GREEN, width=5, joint="curve")

        for px, py in actual_line_points[:-1]:
            draw.ellipse((px - 2.5, py - 2.5, px + 2.5, py + 2.5), fill=COLOR_GREEN)

        current_label_text = widget_primary_value_text(widget, profile_timezone=profile_timezone)
        current_point_x, current_point_y = actual_line_points[-1]
        current_point_fill = COLOR_GREEN

        if (
            target_timestamp is not None
            and target_value is not None
            and now_timestamp > actual_points[-1][0]
            and target_timestamp > actual_points[-1][0]
        ):
            bridge_end_timestamp = min(now_timestamp, target_timestamp)
            bridge_end_value = _forecast_value_at_timestamp(
                bridge_end_timestamp,
                last_actual_timestamp=actual_points[-1][0],
                last_actual_value=actual_points[-1][1],
                target_timestamp=target_timestamp,
                target_value=target_value,
            )
            bridge_points = [
                actual_line_points[-1],
                (chart_x_for(bridge_end_timestamp), chart_y_for(bridge_end_value)),
            ]
            draw.line(bridge_points, fill=COLOR_BLUE, width=5)
            current_point_x, current_point_y = bridge_points[-1]
            current_point_fill = COLOR_BLUE
            current_label_text = _format_chart_value(widget, bridge_end_value)

            if target_timestamp > bridge_end_timestamp:
                future_points = [
                    bridge_points[-1],
                    (chart_x_for(target_timestamp), chart_y_for(target_value)),
                ]
                draw.line(future_points, fill=COLOR_RED, width=5)
                end_point_x, end_point_y = future_points[-1]
            else:
                end_point_x, end_point_y = bridge_points[-1]
        elif target_timestamp is not None and target_value is not None:
            end_point_x = chart_x_for(target_timestamp)
            end_point_y = chart_y_for(target_value)
        else:
            end_point_x = current_point_x
            end_point_y = current_point_y

        draw.ellipse(
            (current_point_x - 8, current_point_y - 8, current_point_x + 8, current_point_y + 8),
            fill=COLOR_WHITE,
        )
        draw.ellipse(
            (current_point_x - 5, current_point_y - 5, current_point_x + 5, current_point_y + 5),
            fill=current_point_fill,
        )

        if target_value is not None:
            draw.ellipse((end_point_x - 6, end_point_y - 6, end_point_x + 6, end_point_y + 6), fill=COLOR_RED)

        current_label_width = draw.textlength(current_label_text, font=point_value_font)
        current_label_x = min(
            max(plot_left, current_point_x + 10),
            plot_left + plot_width - current_label_width,
        )
        current_label_y = max(plot_top + 8, current_point_y - 30)
        draw.text(
            (current_label_x, current_label_y),
            current_label_text,
            font=point_value_font,
            fill=COLOR_TEXT,
        )

        if target_value is not None:
            end_label_text = _format_chart_value(widget, target_value)
            end_label_width = draw.textlength(end_label_text, font=point_value_font)
            end_label_x = min(
                max(plot_left, end_point_x + 10),
                plot_left + plot_width - end_label_width,
            )
            end_label_y = max(plot_top + 8, end_point_y - 30)
            draw.text(
                (end_label_x, end_label_y),
                end_label_text,
                font=point_value_font,
                fill=COLOR_TEXT,
            )
    else:
        empty_font = _font(30, bold=True)
        message = "Not enough history yet"
        message_width = draw.textlength(message, font=empty_font)
        draw.text(
            (chart_x + (chart_width - message_width) / 2, chart_y + chart_height / 2 - 18),
            message,
            font=empty_font,
            fill=COLOR_MUTED,
        )

    return image


def _render_dashboard_preview_image(
    dashboard: DashboardSummary,
    *,
    profile_timezone: str,
) -> Image.Image:
    image = Image.new("RGBA", (PREVIEW_WIDTH, PREVIEW_HEIGHT), COLOR_BG)
    _draw_glows(image)
    draw = ImageDraw.Draw(image)

    panel_bounds = (36, 36, PREVIEW_WIDTH - 36, PREVIEW_HEIGHT - 36)
    draw.rounded_rectangle(panel_bounds, radius=28, fill=COLOR_PANEL, outline=COLOR_PANEL_BORDER, width=2)

    title_font = _font(56, bold=True)
    subtitle_font = _font(28)
    tile_title_font = _font(24, bold=True)
    tile_value_font = _font(40, bold=True)
    tile_meta_font = _font(20)

    title_lines = _wrap_text(draw, dashboard.name, font=title_font, max_width=760, max_lines=2)
    title_y = 82
    for line in title_lines:
        draw.text((76, title_y), line, font=title_font, fill=COLOR_TEXT)
        title_y += 62

    description = dashboard.description or f"{len(dashboard.widgets)} widgets shared read-only"
    description_lines = _wrap_text(draw, description, font=subtitle_font, max_width=760, max_lines=2)
    for line in description_lines:
        draw.text((76, title_y + 8), line, font=subtitle_font, fill=COLOR_MUTED)
        title_y += 34

    badge_text = f"{len(dashboard.widgets)} widgets"
    badge_font = _font(26, bold=True)
    badge_width = int(draw.textlength(badge_text, font=badge_font)) + 30
    draw.rounded_rectangle(
        (PREVIEW_WIDTH - 76 - badge_width, 88, PREVIEW_WIDTH - 76, 128),
        radius=20,
        fill=(255, 255, 255, 28),
        outline=(255, 255, 255, 52),
    )
    draw.text((PREVIEW_WIDTH - 76 - badge_width + 15, 95), badge_text, font=badge_font, fill=COLOR_TEXT)

    tile_width = 500
    tile_height = 170
    start_x = 76
    start_y = 240
    gap = 24
    preview_widgets = dashboard.widgets[:4]
    for index, widget in enumerate(preview_widgets):
        row = index // 2
        column = index % 2
        tile_x = start_x + column * (tile_width + gap)
        tile_y = start_y + row * (tile_height + gap)
        tile_bounds = (tile_x, tile_y, tile_x + tile_width, tile_y + tile_height)
        draw.rounded_rectangle(
            tile_bounds,
            radius=24,
            fill=(255, 255, 255, 16),
            outline=(255, 255, 255, 28),
            width=2,
        )
        title_lines = _wrap_text(
            draw,
            widget.title,
            font=tile_title_font,
            max_width=tile_width - 48,
            max_lines=2,
        )
        current_y = tile_y + 22
        for line in title_lines:
            draw.text((tile_x + 24, current_y), line, font=tile_title_font, fill=COLOR_TEXT)
            current_y += 28
        primary_value = widget_primary_value_text(widget, profile_timezone=profile_timezone)
        draw.text(
            (tile_x + 24, tile_y + 78),
            primary_value,
            font=tile_value_font,
            fill=_widget_accent_color(widget),
        )
        draw.text(
            (tile_x + 24, tile_y + 128),
            widget_type_label(widget.widget_type),
            font=tile_meta_font,
            fill=COLOR_MUTED,
        )

    if len(dashboard.widgets) > 4:
        more_text = f"+{len(dashboard.widgets) - 4} more widgets"
        draw.text((76, PREVIEW_HEIGHT - 88), more_text, font=_font(24, bold=True), fill=COLOR_TEXT)

    return image


def _image_to_png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def render_widget_preview_png(
    widget: WidgetSummary,
    *,
    dashboard_name: str | None,
    profile_timezone: str,
) -> bytes:
    return _image_to_png_bytes(
        _render_widget_preview_image(
            widget,
            dashboard_name=dashboard_name,
            profile_timezone=profile_timezone,
        )
    )


def render_dashboard_preview_png(
    dashboard: DashboardSummary,
    *,
    profile_timezone: str,
) -> bytes:
    return _image_to_png_bytes(
        _render_dashboard_preview_image(
            dashboard,
            profile_timezone=profile_timezone,
        )
    )


def _widget_chart_svg(widget: WidgetSummary, *, compact: bool = False) -> str:
    series_points = _widget_chart_points(widget)
    if len(series_points) < 2:
        return ""

    max_points = 24 if compact else 36
    sampled_points = _sample_series_points(series_points, max_points=max_points)
    sampled_dates = [point[0] for point in sampled_points]
    sampled_values = [point[1] for point in sampled_points]
    target_value = _widget_chart_target(widget)
    minimum, maximum = _normalize_chart_bounds(sampled_values, target_value=target_value)

    width = 320 if compact else 860
    height = 120 if compact else 320
    left_pad = 0 if compact else 88
    right_pad = 0 if compact else 24
    top_pad = 6 if compact else 24
    bottom_pad = 0 if compact else 44
    plot_width = width - left_pad - right_pad
    plot_height = height - top_pad - bottom_pad

    points: list[str] = []
    for index, value in enumerate(sampled_values):
        progress = 0 if len(sampled_values) == 1 else index / (len(sampled_values) - 1)
        x = left_pad + progress * plot_width
        y = top_pad + plot_height - ((value - minimum) / (maximum - minimum)) * plot_height
        points.append(f"{x:.1f},{y:.1f}")

    accent = _widget_accent_color(widget)
    accent_css = f"rgb({accent[0]} {accent[1]} {accent[2]})"
    first_x = points[0].split(",")[0]
    last_x = points[-1].split(",")[0]
    last_y = points[-1].split(",")[1]

    target_line = ""
    if target_value is not None:
        target_y = top_pad + plot_height - ((target_value - minimum) / (maximum - minimum)) * plot_height
        target_line = (
            f'<line x1="{left_pad}" y1="{target_y:.1f}" x2="{left_pad + plot_width}" y2="{target_y:.1f}" '
            'stroke="rgba(255,94,94,0.75)" stroke-width="2" stroke-dasharray="8 8" />'
        )

    area_path = (
        f"M {first_x},{top_pad + plot_height:.1f} "
        f"L {' L '.join(points)} "
        f"L {last_x},{top_pad + plot_height:.1f} Z"
    )

    if compact:
        return (
            f'<svg viewBox="0 0 {width} {height}" aria-hidden="true" preserveAspectRatio="none">'
            '<rect width="100%" height="100%" rx="18" fill="rgba(255,255,255,0.02)" />'
            f"{target_line}"
            f'<path d="{area_path}" fill="rgba({accent[0]},{accent[1]},{accent[2]},0.14)" />'
            f'<polyline fill="none" stroke="{accent_css}" stroke-width="4" stroke-linecap="round" '
            f'stroke-linejoin="round" points="{" ".join(points)}" />'
            f'<circle cx="{last_x}" cy="{last_y}" r="4.5" fill="white" />'
            "</svg>"
        )

    x_start = _format_recorded_at(sampled_dates[0].isoformat())
    x_end = _format_recorded_at(sampled_dates[-1].isoformat())
    y_top = _format_chart_value(widget, maximum)
    y_mid = _format_chart_value(widget, (minimum + maximum) / 2)
    y_bottom = _format_chart_value(widget, minimum)
    y_mid_pos = top_pad + plot_height / 2
    y_bottom_pos = top_pad + plot_height

    grid_lines = "".join(
        (
            f'<line x1="{left_pad}" y1="{y_pos:.1f}" x2="{left_pad + plot_width}" y2="{y_pos:.1f}" '
            'stroke="rgba(255,255,255,0.10)" stroke-width="1" />'
        )
        for y_pos in (top_pad, y_mid_pos, y_bottom_pos)
    )
    axis_labels = "".join(
        [
            (
                f'<text x="0" y="{top_pad + 4:.1f}" fill="rgba(255,255,255,0.62)" '
                f'font-size="14">{escape(y_top)}</text>'
            ),
            (
                f'<text x="0" y="{y_mid_pos + 4:.1f}" fill="rgba(255,255,255,0.56)" '
                f'font-size="14">{escape(y_mid)}</text>'
            ),
            (
                f'<text x="0" y="{y_bottom_pos + 4:.1f}" fill="rgba(255,255,255,0.56)" '
                f'font-size="14">{escape(y_bottom)}</text>'
            ),
            (
                f'<text x="{left_pad}" y="{height - 10}" fill="rgba(255,255,255,0.56)" '
                f'font-size="14">{escape(x_start)}</text>'
            ),
            (
                f'<text x="{left_pad + plot_width}" y="{height - 10}" '
                f'fill="rgba(255,255,255,0.56)" font-size="14" text-anchor="end">'
                f"{escape(x_end)}</text>"
            ),
        ]
    )

    return (
        f'<svg class="widget-chart" viewBox="0 0 {width} {height}" '
        f'aria-label="{escape(widget.title)} chart" preserveAspectRatio="none" role="img">'
        f"{grid_lines}"
        f"{target_line}"
        f'<path d="{area_path}" fill="rgba({accent[0]},{accent[1]},{accent[2]},0.12)" />'
        f'<polyline fill="none" stroke="{accent_css}" stroke-width="4" stroke-linecap="round" '
        f'stroke-linejoin="round" points="{" ".join(points)}" />'
        f'<circle cx="{last_x}" cy="{last_y}" r="5.5" fill="white" />'
        f'<circle cx="{last_x}" cy="{last_y}" r="3.5" fill="{accent_css}" />'
        f"{axis_labels}"
        "</svg>"
    )


def _widget_chart_bootstrap_script(widget: WidgetSummary) -> str:
    payload = json.dumps(widget.model_dump(mode="json"))
    return f"""
(() => {{
  const widget = {payload};
  const chartRoot = document.getElementById("widget-share-chart");
  if (chartRoot === null || window.echarts === undefined) {{
    return;
  }}

  const VALUE_WIDGET_TYPES = new Set([
    "metric_summary",
    "days_since",
    "goal_checklist",
    "goal_summary",
    "goal_completion_percent",
    "goal_success_percent",
    "goal_failure_risk",
  ]);
  if (VALUE_WIDGET_TYPES.has(widget.widget_type)) {{
    return;
  }}

  const chartTheme = {{
    axisLabel: "rgba(255,255,255,0.62)",
    axisLine: "rgba(255,255,255,0.24)",
    gridLine: "rgba(255,255,255,0.10)",
    primary: "#2f7bff",
    success: "#21ff6a",
    danger: "#ff3b3b",
  }};

  function getPaddedNumericAxisBounds(values) {{
    if (values.length === 0) {{
      return null;
    }}
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const range = maximum - minimum;
    if (range > 0) {{
      const padding = range * 0.1;
      return {{ min: minimum - padding, max: maximum + padding }};
    }}
    const baselinePadding = Math.abs(maximum) * 0.1;
    const padding = baselinePadding > 0 ? baselinePadding : 1;
    return {{ min: minimum - padding, max: maximum + padding }};
  }}

  function formatDateOnly(value) {{
    const date = typeof value === "number" ? new Date(value) : new Date(`${{value}}T00:00:00Z`);
    return new Intl.DateTimeFormat("en-US", {{
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    }}).format(date);
  }}

  function metricChartPoints() {{
    return widget.series.map((point) => {{
      if (widget.metric?.metric_type === "date") {{
        return {{
          timestamp: new Date(point.recorded_at).getTime(),
          value: point.date_value === null ? 0 : new Date(`${{point.date_value}}T00:00:00Z`).getTime(),
        }};
      }}
      return {{
        timestamp: new Date(point.recorded_at).getTime(),
        value: point.number_value ?? 0,
      }};
    }});
  }}

  function goalMetricChartPoints() {{
    const goalMetric = widget.goal?.metric;
    if (goalMetric === undefined || goalMetric === null) {{
      return [];
    }}
    return widget.series.flatMap((point) => {{
      if (goalMetric.metric_type === "date") {{
        if (point.date_value === null) {{
          return [];
        }}
        return [{{
          timestamp: new Date(point.recorded_at).getTime(),
          value: new Date(`${{point.date_value}}T00:00:00Z`).getTime(),
        }}];
      }}
      if (point.number_value === null) {{
        return [];
      }}
      return [{{
        timestamp: new Date(point.recorded_at).getTime(),
        value: point.number_value,
      }}];
    }});
  }}

  function goalPercentChartPoints() {{
    return widget.series.map((point) => ({{
      timestamp: new Date(point.recorded_at).getTime(),
      value: point.progress_percent ?? 0,
    }}));
  }}

  function goalTargetEndTimestamp() {{
    if (widget.goal?.target_date === null || widget.goal?.target_date === undefined) {{
      return null;
    }}
    return new Date(`${{widget.goal.target_date}}T23:59:59Z`).getTime();
  }}

  function goalTargetValue() {{
    const goal = widget.goal;
    if (goal === null || goal === undefined) {{
      return null;
    }}
    if (goal.metric === null || goal.metric === undefined) {{
      return null;
    }}
    if (goal.metric.metric_type === "date") {{
      return goal.target_value_date === null
        ? null
        : new Date(`${{goal.target_value_date}}T00:00:00Z`).getTime();
    }}
    return goal.target_value_number;
  }}

  function formatMetricAxisValue(value) {{
    if (widget.metric?.metric_type !== "date") {{
      return value.toFixed(widget.metric?.decimal_places ?? 0);
    }}
    return formatDateOnly(value);
  }}

  function formatGoalMetricAxisValue(value) {{
    if (widget.goal?.metric === null || widget.goal?.metric === undefined) {{
      return `${{Math.round(value)}}%`;
    }}
    if (widget.goal.metric.metric_type !== "date") {{
      return value.toFixed(widget.goal.metric.decimal_places ?? 0);
    }}
    return formatDateOnly(value);
  }}

  function forecastValueAtTimestamp(
    timestamp,
    lastActualTimestamp,
    lastActualValue,
    targetEndTimestamp,
    targetValue,
  ) {{
    if (targetEndTimestamp <= lastActualTimestamp) {{
      return targetValue;
    }}
    const progressRatio = (timestamp - lastActualTimestamp) / (targetEndTimestamp - lastActualTimestamp);
    const projectedValue = lastActualValue + (targetValue - lastActualValue) * progressRatio;
    const lowerBound = Math.min(lastActualValue, targetValue);
    const upperBound = Math.max(lastActualValue, targetValue);
    return Math.max(lowerBound, Math.min(projectedValue, upperBound));
  }}

  function createMetricHistoryOption() {{
    const points = metricChartPoints();
    const numericBounds = widget.metric?.metric_type === "number"
      ? getPaddedNumericAxisBounds(points.map((point) => point.value))
      : null;
    return {{
      animation: false,
      grid: {{ left: 16, right: 16, top: 18, bottom: 28, containLabel: true }},
      tooltip: {{ trigger: "axis" }},
      xAxis: {{
        type: "time",
        axisLine: {{ lineStyle: {{ color: chartTheme.axisLine }} }},
        axisLabel: {{ color: chartTheme.axisLabel, fontSize: 11 }},
      }},
      yAxis: {{
        type: "value",
        min: numericBounds?.min,
        max: numericBounds?.max,
        axisLine: {{ show: false }},
        splitLine: {{ lineStyle: {{ color: chartTheme.gridLine }} }},
        axisLabel: {{
          color: chartTheme.axisLabel,
          formatter: (value) => formatMetricAxisValue(value),
        }},
      }},
      series: [{{
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: points.map((point) => [point.timestamp, point.value]),
        lineStyle: {{ color: chartTheme.primary, width: 3 }},
        itemStyle: {{ color: chartTheme.primary }},
      }}],
    }};
  }}

  function createGoalMetricProgressOption() {{
    const actualPoints = goalMetricChartPoints();
    const targetValue = goalTargetValue();
    const targetEndTimestamp = goalTargetEndTimestamp();
    const nowTimestamp = Date.now();
    const actualSeries = actualPoints.map((point) => [point.timestamp, point.value]);
    const values = actualPoints.map((point) => point.value);
    if (typeof targetValue === "number") {{
      values.push(targetValue);
    }}
    const numericBounds =
      widget.goal?.metric.metric_type === "number" ? getPaddedNumericAxisBounds(values) : null;

    const bridgeSeries = [];
    const futureSeries = [];
    const nowPoint = [];
    const lastActualPoint = actualPoints.at(-1) ?? null;

    if (
      lastActualPoint !== null &&
      typeof targetValue === "number" &&
      targetEndTimestamp !== null &&
      targetEndTimestamp > lastActualPoint.timestamp
    ) {{
      const bridgeEndTimestamp = Math.min(nowTimestamp, targetEndTimestamp);
      if (bridgeEndTimestamp > lastActualPoint.timestamp) {{
        bridgeSeries.push([lastActualPoint.timestamp, lastActualPoint.value]);
        const bridgeEndValue = forecastValueAtTimestamp(
          bridgeEndTimestamp,
          lastActualPoint.timestamp,
          lastActualPoint.value,
          targetEndTimestamp,
          targetValue,
        );
        bridgeSeries.push([bridgeEndTimestamp, bridgeEndValue]);
        nowPoint.push([bridgeEndTimestamp, bridgeEndValue]);
      }}

      if (targetEndTimestamp > nowTimestamp && bridgeSeries.length > 0) {{
        const futureStart = bridgeSeries.at(-1);
        if (futureStart !== undefined) {{
          futureSeries.push(futureStart, [targetEndTimestamp, targetValue]);
        }}
      }}
    }}

    return {{
      animation: false,
      grid: {{ left: 16, right: 16, top: 18, bottom: 28, containLabel: true }},
      tooltip: {{ trigger: "axis" }},
      xAxis: {{
        type: "time",
        axisLine: {{ lineStyle: {{ color: chartTheme.axisLine }} }},
        axisLabel: {{ color: chartTheme.axisLabel, fontSize: 11 }},
      }},
      yAxis: {{
        type: "value",
        min: numericBounds?.min,
        max: numericBounds?.max,
        axisLine: {{ show: false }},
        splitLine: {{ lineStyle: {{ color: chartTheme.gridLine }} }},
        axisLabel: {{
          color: chartTheme.axisLabel,
          formatter: (value) => formatGoalMetricAxisValue(value),
        }},
      }},
      series: [
        {{
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 7,
          data: actualSeries,
          lineStyle: {{ color: chartTheme.success, width: 3 }},
          itemStyle: {{ color: chartTheme.success }},
        }},
        {{
          type: "line",
          smooth: false,
          symbol: "none",
          data: bridgeSeries,
          tooltip: {{ show: false }},
          lineStyle: {{ color: chartTheme.primary, width: 3 }},
        }},
        {{
          type: "scatter",
          symbol: "circle",
          symbolSize: 9,
          data: nowPoint,
          tooltip: {{ show: false }},
          itemStyle: {{ color: chartTheme.primary }},
        }},
        {{
          type: "line",
          smooth: false,
          symbol: "none",
          data: futureSeries,
          tooltip: {{ show: false }},
          lineStyle: {{ color: chartTheme.danger, width: 3 }},
        }},
      ],
    }};
  }}

  function createGoalPercentProgressOption() {{
    const actualPoints = goalPercentChartPoints();
    const targetEndTimestamp = goalTargetEndTimestamp();
    const lastActualPoint = actualPoints.at(-1) ?? null;
    const nowTimestamp = Date.now();
    const bridgeSeries = [];
    const futureSeries = [];

    if (
      lastActualPoint !== null &&
      targetEndTimestamp !== null &&
      targetEndTimestamp > lastActualPoint.timestamp
    ) {{
      const bridgeEndTimestamp = Math.min(nowTimestamp, targetEndTimestamp);
      if (bridgeEndTimestamp > lastActualPoint.timestamp) {{
        bridgeSeries.push([lastActualPoint.timestamp, lastActualPoint.value]);
        bridgeSeries.push([
          bridgeEndTimestamp,
          forecastValueAtTimestamp(
            bridgeEndTimestamp,
            lastActualPoint.timestamp,
            lastActualPoint.value,
            targetEndTimestamp,
            100,
          ),
        ]);
      }}

      if (targetEndTimestamp > nowTimestamp && bridgeSeries.length > 0) {{
        futureSeries.push(bridgeSeries.at(-1), [targetEndTimestamp, 100]);
      }}
    }}

    return {{
      animation: false,
      grid: {{ left: 16, right: 16, top: 18, bottom: 28, containLabel: true }},
      tooltip: {{ trigger: "axis" }},
      xAxis: {{
        type: "time",
        axisLine: {{ lineStyle: {{ color: chartTheme.axisLine }} }},
        axisLabel: {{ color: chartTheme.axisLabel, fontSize: 11 }},
      }},
      yAxis: {{
        type: "value",
        min: 0,
        max: 100,
        axisLabel: {{ color: chartTheme.axisLabel, formatter: "{{value}}%" }},
        splitLine: {{ lineStyle: {{ color: chartTheme.gridLine }} }},
      }},
      series: [
        {{
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 7,
          data: actualPoints.map((point) => [point.timestamp, point.value]),
          lineStyle: {{ color: chartTheme.success, width: 3 }},
          itemStyle: {{ color: chartTheme.success }},
        }},
        {{
          type: "line",
          smooth: true,
          symbol: "none",
          data: bridgeSeries,
          tooltip: {{ show: false }},
          lineStyle: {{ color: chartTheme.primary, width: 3 }},
        }},
        {{
          type: "scatter",
          symbol: "circle",
          symbolSize: 9,
          data: bridgeSeries.length === 0 ? [] : [bridgeSeries[bridgeSeries.length - 1]],
          tooltip: {{ show: false }},
          itemStyle: {{ color: chartTheme.primary }},
        }},
        {{
          type: "line",
          smooth: true,
          symbol: "none",
          data: futureSeries,
          tooltip: {{ show: false }},
          lineStyle: {{ color: chartTheme.danger, width: 3 }},
        }},
      ],
    }};
  }}

  const goalMetricPoints = goalMetricChartPoints();
  const option =
    widget.widget_type === "goal_progress"
      ? (goalMetricPoints.length > 0 ? createGoalMetricProgressOption() : createGoalPercentProgressOption())
      : createMetricHistoryOption();

  const chart = window.echarts.init(chartRoot);
  chart.setOption(option, true);

  const resize = () => chart.resize();
  window.addEventListener("resize", resize);
}})();
"""


def _share_page_styles() -> str:
    return """
      :root {
        --bg: #070a12;
        --panel: rgba(255, 255, 255, 0.06);
        --panel-strong: rgba(255, 255, 255, 0.09);
        --panel-border: rgba(255, 255, 255, 0.10);
        --text: rgba(255, 255, 255, 0.92);
        --muted: rgba(255, 255, 255, 0.65);
        --faint: rgba(255, 255, 255, 0.5);
        --green: #21ff6a;
        --blue: #2f7bff;
        --red: #ff3b3b;
      }

      html, body {
        margin: 0;
        min-height: 100%;
        background:
          radial-gradient(1200px 600px at 20% 0%, rgba(33, 255, 106, 0.10), transparent 55%),
          radial-gradient(900px 500px at 85% 20%, rgba(47, 123, 255, 0.10), transparent 60%),
          var(--bg);
        color: var(--text);
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      }

      body {
        padding: 40px 16px 56px;
      }

      .shell {
        max-width: 1080px;
        margin: 0 auto;
        display: grid;
        gap: 24px;
      }

      .hero,
      .panel,
      .widget-card {
        background: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 20px;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(10px);
      }

      .hero {
        padding: 24px;
        display: grid;
        gap: 12px;
      }

      .eyebrow {
        margin: 0;
        color: var(--faint);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      h1 {
        margin: 0;
        font-size: clamp(2rem, 5vw, 3.4rem);
        line-height: 1.05;
      }

      .summary {
        margin: 0;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
      }

      .panel {
        padding: 18px;
      }

      .preview-image {
        width: 100%;
        display: block;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.08);
      }

      .chart-panel {
        padding: 18px 18px 12px;
        display: grid;
        gap: 16px;
      }

      .chart-panel-head {
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        justify-content: space-between;
        gap: 12px;
      }

      .chart-panel-copy {
        display: grid;
        gap: 8px;
      }

      .chart-panel-copy h2 {
        margin: 0;
        font-size: 1.15rem;
      }

      .chart-panel-copy p {
        margin: 0;
        color: var(--muted);
      }

      .chart-value {
        font-size: clamp(2rem, 5vw, 3.5rem);
        font-weight: 800;
        line-height: 1;
      }

      .chart-stage {
        min-height: 26rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 0;
      }

      .chart-stage svg,
      .chart-stage .widget-chart {
        width: 100%;
        height: 100%;
        display: block;
      }

      .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
        gap: 14px;
      }

      .detail-card {
        padding: 16px;
        border-radius: 16px;
        background: var(--panel-strong);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }

      .detail-card span {
        display: block;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--faint);
        margin-bottom: 8px;
      }

      .detail-card strong {
        font-size: 1rem;
        line-height: 1.4;
      }

      .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
        gap: 18px;
      }

      .widget-card {
        padding: 18px;
        display: grid;
        gap: 12px;
      }

      .widget-card h2 {
        margin: 0;
        font-size: 1.15rem;
        line-height: 1.3;
      }

      .widget-meta {
        color: var(--faint);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .widget-value {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
      }

      .widget-copy {
        margin: 0;
        color: var(--muted);
        line-height: 1.5;
      }

      .sparkline {
        height: 8rem;
      }

      .sparkline svg {
        width: 100%;
        height: 100%;
        display: block;
      }

      @media (max-width: 720px) {
        body {
          padding-top: 24px;
        }

        .hero,
        .panel,
        .widget-card {
          border-radius: 16px;
        }
      }
    """


def _share_page_html(
    *,
    title: str,
    description: str | None,
    image_url: str,
    share_url: str,
    body_html: str,
    body_end_html: str = "",
    head_end_html: str = "",
) -> str:
    escaped_title = escape(title)
    escaped_image_url = escape(image_url, quote=True)
    escaped_share_url = escape(share_url, quote=True)
    description_meta = ""
    if description is not None and description != "":
        escaped_description = escape(description)
        description_meta = f"""
  <meta name="description" content="{escaped_description}" />
  <meta property="og:description" content="{escaped_description}" />
  <meta name="twitter:description" content="{escaped_description}" />"""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="robots" content="noindex,nofollow" />
  <meta property="og:title" content="{escaped_title}" />
  {description_meta}
  <meta property="og:image" content="{escaped_image_url}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{escaped_share_url}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{escaped_title}" />
  <meta name="twitter:image" content="{escaped_image_url}" />
  <title>{escaped_title}</title>
  <style>{_share_page_styles()}</style>
  {head_end_html}
</head>
<body>
{body_html}
{body_end_html}
</body>
</html>
"""


def render_widget_share_page(
    widget: WidgetSummary,
    *,
    dashboard_name: str | None,
    profile_timezone: str,
    share_url: str,
    preview_url: str,
) -> str:
    title = widget_og_title(widget, profile_timezone=profile_timezone)
    chart_script = _widget_chart_bootstrap_script(widget)
    chart_html = (
        """
    <section class="panel chart-panel">
      <div class="chart-panel-head">
        <div class="chart-panel-copy">
          <h2>Widget graph</h2>
          <p>Interactive shared chart</p>
        </div>
        <div class="chart-value">
          """
        + escape(widget_primary_value_text(widget, profile_timezone=profile_timezone))
        + """
        </div>
      </div>
      <div class="chart-stage">
        <div id="widget-share-chart" class="widget-chart" aria-label="Shared widget chart"></div>
      </div>
    </section>
"""
    )
    body_html = f"""
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Shared widget</p>
      <h1>{escape(widget.title)}</h1>
      <p class="summary">
        {escape(widget_detail_text(widget, profile_timezone=profile_timezone))}
      </p>
    </section>
    {chart_html}
    <section class="detail-grid">
      <article class="detail-card">
        <span>Type</span>
        <strong>{escape(widget_type_label(widget.widget_type))}</strong>
      </article>
      <article class="detail-card">
        <span>Primary value</span>
        <strong>
          {escape(widget_primary_value_text(widget, profile_timezone=profile_timezone))}
        </strong>
      </article>
      <article class="detail-card">
        <span>Dashboard</span>
        <strong>{escape(dashboard_name or "Shared widget")}</strong>
      </article>
    </section>
  </main>
"""
    return _share_page_html(
        title=title,
        description=None,
        image_url=preview_url,
        share_url=share_url,
        body_html=body_html,
        head_end_html='<script src="/vendor/echarts.min.js"></script>',
        body_end_html=f"<script>{chart_script}</script>",
    )


def render_dashboard_share_page(
    dashboard: DashboardSummary,
    *,
    profile_timezone: str,
    share_url: str,
    preview_url: str,
) -> str:
    title = f"{dashboard.name} | Goal Tracker"
    description = dashboard_og_description(dashboard, profile_timezone=profile_timezone)

    widget_cards = []
    for widget in dashboard.widgets:
        sparkline = _widget_chart_svg(widget, compact=True)
        sparkline_html = (
            f'<div class="sparkline">{sparkline}</div>'
            if sparkline != ""
            else '<p class="widget-copy">Not enough history yet.</p>'
        )
        widget_cards.append(
            f"""
      <article class="widget-card">
        <div class="widget-meta">{escape(widget_type_label(widget.widget_type))}</div>
        <h2>{escape(widget.title)}</h2>
        <div class="widget-value">
          {escape(widget_primary_value_text(widget, profile_timezone=profile_timezone))}
        </div>
        <p class="widget-copy">
          {escape(widget_detail_text(widget, profile_timezone=profile_timezone))}
        </p>
        {sparkline_html}
      </article>
"""
        )

    body_html = f"""
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Shared dashboard</p>
      <h1>{escape(dashboard.name)}</h1>
      <p class="summary">{escape(dashboard.description or "Read-only dashboard share.")}</p>
    </section>
    <section class="panel">
      <img
        class="preview-image"
        src="{escape(preview_url, quote=True)}"
        alt="{escape(dashboard.name)} preview"
      />
    </section>
    <section class="dashboard-grid">
      {
        "".join(widget_cards)
        if widget_cards
        else '<article class="widget-card"><p class="widget-copy">No widgets yet.</p></article>'
    }
    </section>
  </main>
"""
    return _share_page_html(
        title=title,
        description=description,
        image_url=preview_url,
        share_url=share_url,
        body_html=body_html,
    )
