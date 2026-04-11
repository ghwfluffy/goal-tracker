// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DashboardWidgetSummary } from "../lib/api";
import DashboardWidgetChart from "./DashboardWidgetChart.vue";

class ResizeObserverMock {
  observe = vi.fn();
  disconnect = vi.fn();
}

function buildGoalWidget(
  overrides: Partial<DashboardWidgetSummary> = {},
): DashboardWidgetSummary {
  return {
    current_progress_percent: 40,
    display_order: 1,
    failure_risk_percent: 12,
    goal: {
      exception_dates: [],
      id: "goal-1",
      metric: {
        decimal_places: 1,
        id: "metric-1",
        latest_entry: null,
        metric_type: "number",
        name: "Weight",
        unit_label: "lbs",
      },
      start_date: "2026-04-01",
      success_threshold_percent: null,
      target_date: "2026-06-01",
      target_value_date: null,
      target_value_number: 220,
      title: "Reach 220",
    },
    grid_h: 4,
    grid_w: 6,
    grid_x: 0,
    grid_y: 0,
    id: "widget-1",
    metric: null,
    rolling_window_days: null,
    series: [],
    target_met: false,
    time_completion_percent: 18,
    title: "Cut Progress",
    widget_type: "goal_progress",
    ...overrides,
  };
}

describe("DashboardWidgetChart", () => {
  const setOptionMock = vi.fn();
  const resizeMock = vi.fn();
  const disposeMock = vi.fn();
  const globalWindow = globalThis as typeof globalThis & {
    echarts?: {
      init: ReturnType<typeof vi.fn>;
    };
  };

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-11T17:00:00Z"));

    setOptionMock.mockReset();
    resizeMock.mockReset();
    disposeMock.mockReset();

    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    globalWindow.echarts = {
      init: vi.fn(() => ({
        dispose: disposeMock,
        resize: resizeMock,
        setOption: setOptionMock,
      })),
    };
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    delete globalWindow.echarts;
  });

  it("plots numeric goal progress with metric values and target forecast", async () => {
    mount(DashboardWidgetChart, {
      attachTo: document.body,
      props: {
        widget: buildGoalWidget({
          series: [
            {
              date_value: null,
              number_value: 250,
              progress_percent: 0,
              recorded_at: "2026-04-01T05:00:00Z",
            },
            {
              date_value: null,
              number_value: 238,
              progress_percent: 40,
              recorded_at: "2026-04-05T12:00:00Z",
            },
          ],
        }),
      },
    });

    await nextTick();

    const option = setOptionMock.mock.calls[0]?.[0] as {
      series: Array<{ data: Array<[number, number]> }>;
      yAxis: { max?: number };
    };

    expect(option.yAxis.max).toBeUndefined();
    expect(option.series[0]?.data).toEqual([
      [new Date("2026-04-01T05:00:00Z").getTime(), 250],
      [new Date("2026-04-05T12:00:00Z").getTime(), 238],
    ]);
    expect(option.series[2]?.data.at(-1)).toEqual([
      new Date("2026-06-01T23:59:59").getTime(),
      220,
    ]);
  });

  it("falls back to percentage progress when the series has no metric values", async () => {
    mount(DashboardWidgetChart, {
      attachTo: document.body,
      props: {
        widget: buildGoalWidget({
          current_progress_percent: 77.78,
          goal: {
            exception_dates: ["2026-04-03"],
            id: "goal-2",
            metric: {
              decimal_places: null,
              id: "metric-2",
              latest_entry: null,
              metric_type: "date",
              name: "Last drink",
              unit_label: null,
            },
            start_date: "2026-04-01",
            success_threshold_percent: 80,
            target_date: "2026-04-10",
            target_value_date: null,
            target_value_number: null,
            title: "No drinking window",
          },
          series: [
            {
              date_value: null,
              number_value: null,
              progress_percent: 100,
              recorded_at: "2026-04-02T20:00:00Z",
            },
            {
              date_value: null,
              number_value: null,
              progress_percent: 77.78,
              recorded_at: "2026-04-05T20:00:00Z",
            },
          ],
        }),
      },
    });

    await nextTick();

    const option = setOptionMock.mock.calls[0]?.[0] as {
      series: Array<{ data: Array<[number, number]> }>;
      yAxis: { max?: number };
    };

    expect(option.yAxis.max).toBe(100);
    expect(option.series[0]?.data).toEqual([
      [new Date("2026-04-02T20:00:00Z").getTime(), 100],
      [new Date("2026-04-05T20:00:00Z").getTime(), 77.78],
    ]);
    expect(option.series[1]?.data.at(-1)).toEqual([
      new Date("2026-04-10T23:59:59").getTime(),
      100,
    ]);
    expect(option.series[2]?.data).toEqual([]);
  });
});
