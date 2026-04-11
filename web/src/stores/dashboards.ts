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
        await createDashboardWidget(dashboardId, payload);
        await this.loadDashboards();
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
        await updateDashboardWidget(dashboardId, widgetId, payload);
        await this.loadDashboards();
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
        await this.loadDashboards();
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
