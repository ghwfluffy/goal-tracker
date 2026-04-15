import type { DashboardWidgetSummary } from "./api";
import { isNumericMetricType } from "./tracking";
import {
  DEFAULT_PROFILE_TIMEZONE,
  daysBetweenDateOnly,
  formatDateOnly,
  getCurrentDateInTimezone,
} from "./time";

export const DASHBOARD_VALUE_WIDGET_TYPES = new Set<DashboardWidgetSummary["widget_type"]>([
  "metric_summary",
  "days_since",
  "goal_checklist",
  "goal_summary",
  "goal_completion_percent",
  "goal_success_percent",
  "goal_failure_risk",
]);

export const DASHBOARD_MOBILE_COMPACT_WIDGET_TYPES = new Set<DashboardWidgetSummary["widget_type"]>([
  "metric_summary",
  "days_since",
  "goal_checklist",
  "goal_summary",
  "goal_completion_percent",
  "goal_success_percent",
  "goal_failure_risk",
]);

export function isDashboardValueWidget(widgetType: DashboardWidgetSummary["widget_type"]): boolean {
  return DASHBOARD_VALUE_WIDGET_TYPES.has(widgetType);
}

export function isDashboardMobileCompactWidget(widgetType: DashboardWidgetSummary["widget_type"]): boolean {
  return DASHBOARD_MOBILE_COMPACT_WIDGET_TYPES.has(widgetType);
}

export function isDashboardPercentWidget(
  widgetType: DashboardWidgetSummary["widget_type"],
): boolean {
  return (
    widgetType === "goal_summary" ||
    widgetType === "goal_completion_percent" ||
    widgetType === "goal_success_percent" ||
    widgetType === "goal_failure_risk"
  );
}

export function getDashboardWidgetPercentValue(widget: DashboardWidgetSummary): number | null {
  if (!isDashboardPercentWidget(widget.widget_type)) {
    return null;
  }

  if (widget.widget_type === "goal_completion_percent") {
    return widget.time_completion_percent;
  }

  if (widget.widget_type === "goal_failure_risk") {
    return widget.failure_risk_percent;
  }

  return widget.current_progress_percent;
}

export function getDashboardWidgetPercentLabel(widget: DashboardWidgetSummary): string {
  if (widget.widget_type === "goal_completion_percent") {
    return "Timeline";
  }

  if (widget.widget_type === "goal_success_percent") {
    return "Success";
  }

  if (widget.widget_type === "goal_failure_risk") {
    return "Failure risk";
  }

  if (widget.widget_type === "goal_summary") {
    if (widget.target_met === true) {
      return "On target";
    }
    if (widget.target_met === false) {
      return "Below target";
    }
  }

  return "Goal progress";
}

export function getDashboardWidgetValueText(
  widget: DashboardWidgetSummary,
  timezone: string = DEFAULT_PROFILE_TIMEZONE,
): string {
  if (widget.widget_type === "metric_summary") {
    const metric = widget.metric;
    const latestEntry = metric?.latest_entry;
    if (metric === null || metric === undefined || latestEntry === null || latestEntry === undefined) {
      return "No value";
    }
    if (isNumericMetricType(metric.metric_type)) {
      const numberValue = latestEntry.number_value;
      if (numberValue === null) {
        return "No value";
      }
      const formatted = numberValue.toFixed(metric.decimal_places ?? 0);
      return metric.unit_label ? `${formatted} ${metric.unit_label}` : formatted;
    }
    if (latestEntry.date_value === null) {
      return "No value";
    }
    return formatDateOnly(latestEntry.date_value);
  }

  if (widget.widget_type === "days_since") {
    const latestEntry = widget.metric?.latest_entry;
    if (widget.metric?.metric_type !== "date" || latestEntry?.date_value === null || latestEntry === null) {
      return "No value";
    }

    const today = getCurrentDateInTimezone(timezone);
    const daysSince = daysBetweenDateOnly(latestEntry.date_value, today);
    if (daysSince < 0) {
      return "0 days";
    }
    return daysSince === 1 ? "1 day" : `${daysSince} days`;
  }

  if (widget.widget_type === "goal_checklist") {
    const goal = widget.goal;
    if (goal === null) {
      return "No value";
    }
    return `${goal.checklist_completed_count}/${goal.checklist_total_count} done`;
  }

  if (widget.widget_type === "goal_summary" && widget.goal?.goal_type === "checklist") {
    return `${widget.goal.checklist_completed_count}/${widget.goal.checklist_total_count} done`;
  }

  const percentValue = getDashboardWidgetPercentValue(widget);

  if (percentValue === null) {
    return "No value";
  }
  return `${Math.round(percentValue)}%`;
}
