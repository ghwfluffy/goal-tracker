import { defineStore } from "pinia";

import {
  createDashboard,
  createDashboardWidget,
  deleteDashboard,
  deleteDashboardWidget,
  fetchDashboards,
  updateDashboard,
  updateDashboardWidget,
  type CreateDashboardPayload,
  type CreateDashboardWidgetPayload,
  type DashboardSummary,
  type UpdateDashboardPayload,
  type UpdateDashboardWidgetPayload,
} from "../lib/api";

type DashboardsViewState = "idle" | "loading" | "ready" | "error";
type DashboardsSubmissionState = "idle" | "submitting";

interface DashboardsStoreState {
  dashboards: DashboardSummary[];
  errorMessage: string;
  submissionState: DashboardsSubmissionState;
  viewState: DashboardsViewState;
}

function upsertWidget(
  dashboards: DashboardSummary[],
  dashboardId: string,
  widget: DashboardSummary["widgets"][number],
): DashboardSummary[] {
  return dashboards.map((dashboard) => {
    if (dashboard.id !== dashboardId) {
      return dashboard;
    }

    const nextWidgets = dashboard.widgets.some((candidate) => candidate.id === widget.id)
      ? dashboard.widgets.map((candidate) => (candidate.id === widget.id ? widget : candidate))
      : [...dashboard.widgets, widget];

    return {
      ...dashboard,
      widgets: [...nextWidgets].sort((left, right) => left.display_order - right.display_order),
    };
  });
}

function removeWidgetFromDashboard(
  dashboards: DashboardSummary[],
  dashboardId: string,
  widgetId: string,
): DashboardSummary[] {
  return dashboards.map((dashboard) => {
    if (dashboard.id !== dashboardId) {
      return dashboard;
    }

    return {
      ...dashboard,
      widgets: dashboard.widgets.filter((widget) => widget.id !== widgetId),
    };
  });
}

export const useDashboardsStore = defineStore("dashboards", {
  state: (): DashboardsStoreState => ({
    dashboards: [],
    errorMessage: "",
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.dashboards = [];
      this.errorMessage = "";
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadDashboards(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchDashboards();
        this.dashboards = response.dashboards;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load dashboards.";
        this.viewState = "error";
      }
    },
    async createDashboard(payload: CreateDashboardPayload): Promise<string | null> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const createdDashboard = await createDashboard(payload);
        await this.loadDashboards();
        return createdDashboard.id;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to create the dashboard.";
        return null;
      } finally {
        this.submissionState = "idle";
      }
    },
    async updateDashboard(dashboardId: string, payload: UpdateDashboardPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateDashboard(dashboardId, payload);
        await this.loadDashboards();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to update the dashboard.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async deleteDashboard(dashboardId: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await deleteDashboard(dashboardId);
        await this.loadDashboards();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to delete the dashboard.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async createWidget(
      dashboardId: string,
      payload: CreateDashboardWidgetPayload,
    ): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const createdWidget = await createDashboardWidget(dashboardId, payload);
        this.dashboards = upsertWidget(this.dashboards, dashboardId, createdWidget);
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to add the widget.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async updateWidget(
      dashboardId: string,
      widgetId: string,
      payload: UpdateDashboardWidgetPayload,
    ): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const updatedWidget = await updateDashboardWidget(dashboardId, widgetId, payload);
        if (payload.layout_mode === "mobile") {
          await this.loadDashboards();
        } else {
          this.dashboards = upsertWidget(this.dashboards, dashboardId, updatedWidget);
        }
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to update the widget.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async deleteWidget(dashboardId: string, widgetId: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await deleteDashboardWidget(dashboardId, widgetId);
        this.dashboards = removeWidgetFromDashboard(this.dashboards, dashboardId, widgetId);
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to delete the widget.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
