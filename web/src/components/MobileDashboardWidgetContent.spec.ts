// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { DashboardWidgetSummary } from "../lib/api";
import MobileDashboardWidgetContent from "./MobileDashboardWidgetContent.vue";

function buildWidget(overrides: Partial<DashboardWidgetSummary> = {}): DashboardWidgetSummary {
  return {
    current_progress_percent: 40,
    display_order: 1,
    failure_risk_percent: 12,
    forecast_algorithm: null,
    goal: null,
    grid_h: 3,
    grid_w: 4,
    grid_x: 0,
    grid_y: 0,
    id: "widget-1",
    metric: {
      decimal_places: 1,
      id: "metric-1",
      latest_entry: {
        date_value: null,
        id: "entry-1",
        number_value: 245.2,
        recorded_at: "2026-04-11T12:00:00Z",
      },
      metric_type: "number",
      name: "Weight",
      unit_label: "lbs",
    },
    rolling_window_days: null,
    series: [],
    target_met: false,
    time_completion_percent: 18,
    title: "Weight snapshot",
    widget_type: "metric_summary",
    ...overrides,
  };
}

describe("MobileDashboardWidgetContent", () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders compact value widgets without the chart renderer", () => {
    const wrapper = mount(MobileDashboardWidgetContent, {
      global: {
        plugins: [pinia],
      },
      props: {
        widget: buildWidget(),
      },
    });

    expect(wrapper.text()).toContain("245.2 lbs");
    expect(wrapper.find(".mobile-value-widget").exists()).toBe(true);
    expect(wrapper.findComponent({ name: "DashboardWidgetChart" }).exists()).toBe(false);
  });

  it("shows a compact empty state for missing value widgets", () => {
    const wrapper = mount(MobileDashboardWidgetContent, {
      global: {
        plugins: [pinia],
      },
      props: {
        widget: buildWidget({
          metric: {
            decimal_places: 1,
            id: "metric-1",
            latest_entry: null,
            metric_type: "number",
            name: "Weight",
            unit_label: "lbs",
          },
        }),
      },
    });

    expect(wrapper.text()).toContain("No value yet");
    expect(wrapper.get(".mobile-value-widget").classes()).toContain("is-empty");
  });

  it("keeps chart widgets on the chart renderer path", () => {
    const wrapper = mount(MobileDashboardWidgetContent, {
      global: {
        plugins: [pinia],
        stubs: {
          DashboardWidgetChart: {
            name: "DashboardWidgetChart",
            template: "<div class='chart-stub'>chart</div>",
          },
        },
      },
      props: {
        widget: buildWidget({
          metric: null,
          series: [
            {
              date_value: null,
              number_value: 245.2,
              progress_percent: null,
              recorded_at: "2026-04-11T12:00:00Z",
            },
          ],
          title: "Weight trend",
          widget_type: "metric_history",
        }),
      },
    });

    expect(wrapper.find(".mobile-chart-widget").exists()).toBe(true);
    expect(wrapper.find(".chart-stub").exists()).toBe(true);
  });
});
