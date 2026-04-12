import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DashboardSummary, DashboardWidgetSummary } from "../lib/api";
import { useDashboardsStore } from "./dashboards";

const {
  createDashboardWidgetMock,
  deleteDashboardWidgetMock,
  fetchDashboardsMock,
  updateDashboardWidgetMock,
} = vi.hoisted(() => ({
  createDashboardWidgetMock: vi.fn(),
  deleteDashboardWidgetMock: vi.fn(),
  fetchDashboardsMock: vi.fn(),
  updateDashboardWidgetMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    createDashboardWidget: createDashboardWidgetMock,
    deleteDashboardWidget: deleteDashboardWidgetMock,
    fetchDashboards: fetchDashboardsMock,
    updateDashboardWidget: updateDashboardWidgetMock,
  };
});

function buildWidget(overrides: Partial<DashboardWidgetSummary> = {}): DashboardWidgetSummary {
  return {
    current_progress_percent: null,
    display_order: 1,
    failure_risk_percent: null,
    forecast_algorithm: null,
    goal: null,
    grid_h: 3,
    grid_w: 6,
    grid_x: 0,
    grid_y: 0,
    id: "widget-1",
    metric: null,
    mobile_grid_h: 3,
    mobile_grid_w: 1,
    mobile_grid_x: 0,
    mobile_grid_y: 0,
    rolling_window_days: 30,
    series: [],
    target_met: null,
    time_completion_percent: null,
    title: "Weight trend",
    widget_type: "metric_history",
    ...overrides,
  };
}

function buildDashboard(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    description: null,
    id: "dashboard-1",
    is_default: true,
    name: "Main dashboard",
    widgets: [buildWidget()],
    ...overrides,
  };
}

describe("useDashboardsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    createDashboardWidgetMock.mockReset();
    deleteDashboardWidgetMock.mockReset();
    fetchDashboardsMock.mockReset();
    updateDashboardWidgetMock.mockReset();
  });

  it("updates a widget in place without reloading dashboards", async () => {
    const store = useDashboardsStore();
    store.viewState = "ready";
    store.dashboards = [buildDashboard()];

    updateDashboardWidgetMock.mockResolvedValue(
      buildWidget({
        grid_h: 5,
        grid_w: 12,
        grid_y: 4,
        rolling_window_days: 90,
      }),
    );

    await expect(
      store.updateWidget("dashboard-1", "widget-1", {
        grid_h: 5,
        grid_w: 12,
        grid_y: 4,
        rolling_window_days: 90,
      }),
    ).resolves.toBe(true);

    expect(updateDashboardWidgetMock).toHaveBeenCalledWith("dashboard-1", "widget-1", {
      grid_h: 5,
      grid_w: 12,
      grid_y: 4,
      rolling_window_days: 90,
    });
    expect(fetchDashboardsMock).not.toHaveBeenCalled();
    expect(store.viewState).toBe("ready");
    expect(store.dashboards[0]?.widgets[0]).toMatchObject({
      grid_h: 5,
      grid_w: 12,
      grid_y: 4,
      rolling_window_days: 90,
    });
  });

  it("reloads dashboards after a mobile layout update", async () => {
    const store = useDashboardsStore();
    store.viewState = "ready";
    store.dashboards = [buildDashboard()];
    fetchDashboardsMock.mockResolvedValue({
      dashboards: [
        buildDashboard({
          widgets: [buildWidget({ mobile_grid_y: 3 }), buildWidget({ id: "widget-2", mobile_grid_y: 0 })],
        }),
      ],
    });
    updateDashboardWidgetMock.mockResolvedValue(buildWidget({ mobile_grid_y: 3 }));

    await expect(
      store.updateWidget("dashboard-1", "widget-1", {
        grid_y: 3,
        layout_mode: "mobile",
      }),
    ).resolves.toBe(true);

    expect(fetchDashboardsMock).toHaveBeenCalledTimes(1);
  });
});
