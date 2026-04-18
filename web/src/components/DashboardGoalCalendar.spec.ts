// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { DashboardWidgetSummary } from "../lib/api";
import DashboardGoalCalendar from "./DashboardGoalCalendar.vue";

function buildWidget(overrides: Partial<DashboardWidgetSummary> = {}): DashboardWidgetSummary {
  return {
    calendar: {
      days: [
        {
          date: "2026-04-05",
          goal_statuses: [],
          is_in_range: false,
          status: "blank",
        },
        {
          date: "2026-04-06",
          goal_statuses: [
            {
              goal_id: "goal-1",
              result_label: "Submitted",
              status: "success",
              subject: "Weight",
            },
            {
              goal_id: "goal-2",
              result_label: "Missing",
              status: "pending",
              subject: "Cardio",
            },
          ],
          is_in_range: true,
          status: "pending",
        },
      ],
      ends_on: "2026-04-06",
      goal_count: 2,
      goal_scope: "selected",
      grid_ends_on: "2026-04-11",
      grid_starts_on: "2026-04-05",
      period: "current_month",
      starts_on: "2026-04-06",
    },
    calendar_period: "current_month",
    current_progress_percent: null,
    display_order: 1,
    failure_risk_percent: null,
    forecast_algorithm: null,
    goal: null,
    grid_h: 5,
    grid_w: 8,
    grid_x: 0,
    grid_y: 0,
    goal_scope: "selected",
    goals: [],
    id: "widget-calendar",
    metric: null,
    mobile_grid_h: 5,
    mobile_order: 0,
    mobile_grid_w: 1,
    mobile_grid_x: 0,
    mobile_grid_y: 0,
    rolling_window_days: null,
    series: [],
    target_met: null,
    time_completion_percent: null,
    title: "Goal calendar",
    widget_type: "goal_calendar",
    ...overrides,
  };
}

describe("DashboardGoalCalendar", () => {
  it("opens a day details popup with the goal breakdown", async () => {
    const wrapper = mount(DashboardGoalCalendar, {
      global: {
        stubs: {
          Dialog: {
            props: ["visible", "header"],
            template:
              "<div v-if='visible' class='dialog-stub'><h2>{{ header }}</h2><slot /></div>",
          },
        },
      },
      props: {
        widget: buildWidget(),
      },
    });

    await wrapper.get("button[aria-label='Show details for 2026-04-06']").trigger("click");

    expect(wrapper.text()).toContain("Monday, April 6, 2026");
    expect(wrapper.text()).toContain("Weight");
    expect(wrapper.text()).toContain("Submitted");
    expect(wrapper.text()).toContain("Cardio");
    expect(wrapper.text()).toContain("Missing");
  });

  it("emits an update request when the missing result is clicked", async () => {
    const wrapper = mount(DashboardGoalCalendar, {
      global: {
        stubs: {
          Dialog: {
            props: ["visible", "header"],
            template:
              "<div v-if='visible' class='dialog-stub'><h2>{{ header }}</h2><slot /></div>",
          },
        },
      },
      props: {
        widget: buildWidget(),
      },
    });

    await wrapper.get("button[aria-label='Show details for 2026-04-06']").trigger("click");
    await wrapper.get(".goal-calendar-detail-action").trigger("click");

    expect(wrapper.emitted("openMissingUpdate")).toEqual([
      [{ date: "2026-04-06", goalId: "goal-2" }],
    ]);
  });
});
