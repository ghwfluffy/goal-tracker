import { describe, expect, it } from "vitest";

import type {
  DashboardGoalReference,
  DashboardMetricReference,
  DashboardWidgetSummary,
} from "./api";
import { getDashboardWidgetEntryMetricId } from "./dashboardWidgets";

const metric: DashboardMetricReference = {
  decimal_places: 1,
  id: "metric-1",
  latest_entry: null,
  metric_type: "number",
  name: "Weight",
  unit_label: "lbs",
};

function buildGoal(overrides: Partial<DashboardGoalReference> = {}): DashboardGoalReference {
  return {
    checklist_completed_count: 0,
    checklist_items: [],
    checklist_total_count: 0,
    exception_dates: [],
    goal_type: "metric",
    id: "goal-1",
    metric,
    start_date: "2026-06-01",
    success_threshold_percent: null,
    target_date: "2026-08-01",
    target_value_date: null,
    target_value_number: 220,
    title: "Reach 220",
    ...overrides,
  };
}

function buildWidget(overrides: Partial<DashboardWidgetSummary> = {}): DashboardWidgetSummary {
  return {
    calendar: null,
    calendar_period: null,
    current_progress_percent: null,
    display_order: 0,
    failure_risk_percent: null,
    forecast_algorithm: null,
    goal: null,
    goal_scope: null,
    goals: [],
    grid_h: 3,
    grid_w: 4,
    grid_x: 0,
    grid_y: 0,
    id: "widget-1",
    metric: null,
    mobile_order: 0,
    rolling_window_days: null,
    series: [],
    target_met: null,
    time_completion_percent: null,
    title: "Widget",
    widget_type: "metric_summary",
    ...overrides,
  };
}

describe("getDashboardWidgetEntryMetricId", () => {
  it("returns the metric for a metric widget", () => {
    expect(getDashboardWidgetEntryMetricId(buildWidget({ metric }))).toBe("metric-1");
  });

  it("returns the backing metric for a goal widget", () => {
    expect(
      getDashboardWidgetEntryMetricId(
        buildWidget({ goal: buildGoal(), widget_type: "goal_progress" }),
      ),
    ).toBe("metric-1");
  });

  it("returns a shared metric for a multi-goal widget only when unambiguous", () => {
    expect(
      getDashboardWidgetEntryMetricId(
        buildWidget({ goals: [buildGoal(), buildGoal({ id: "goal-2" })] }),
      ),
    ).toBe("metric-1");

    expect(
      getDashboardWidgetEntryMetricId(
        buildWidget({
          goals: [
            buildGoal(),
            buildGoal({ id: "goal-2", metric: { ...metric, id: "metric-2" } }),
          ],
        }),
      ),
    ).toBeNull();
  });

  it("returns no metric for a checklist widget", () => {
    expect(
      getDashboardWidgetEntryMetricId(
        buildWidget({
          goal: buildGoal({ goal_type: "checklist", metric: null }),
          widget_type: "goal_checklist",
        }),
      ),
    ).toBeNull();
  });
});
