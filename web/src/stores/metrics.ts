import { defineStore } from "pinia";

import {
  addMetricEntry,
  createMetric,
  deleteMetric,
  fetchMetrics,
  importMetricEntries,
  updateMetric,
  type CreateMetricEntryPayload,
  type CreateMetricPayload,
  type ImportMetricEntriesPayload,
  type MetricSummary,
  type UpdateMetricPayload,
} from "../lib/api";

type MetricsViewState = "idle" | "loading" | "ready" | "error";
type MetricsSubmissionState = "idle" | "submitting";

interface MetricsStoreState {
  errorMessage: string;
  includeArchived: boolean;
  metrics: MetricSummary[];
  submissionState: MetricsSubmissionState;
  viewState: MetricsViewState;
}

export const useMetricsStore = defineStore("metrics", {
  state: (): MetricsStoreState => ({
    errorMessage: "",
    includeArchived: false,
    metrics: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.includeArchived = false;
      this.metrics = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadMetrics(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchMetrics(this.includeArchived);
        this.metrics = response.metrics;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load metrics.";
        this.viewState = "error";
      }
    },
    async createMetric(payload: CreateMetricPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await createMetric(payload);
        await this.loadMetrics();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to create metric.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async updateMetricDetails(metricId: string, payload: UpdateMetricPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateMetric(metricId, payload);
        await this.loadMetrics();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to update metric.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async addMetricEntry(metricId: string, payload: CreateMetricEntryPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await addMetricEntry(metricId, payload);
        await this.loadMetrics();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to update metric.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async importMetricEntries(
      metricId: string,
      payload: ImportMetricEntriesPayload,
    ): Promise<{ importedCount: number; skippedCount: number } | null> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const response = await importMetricEntries(metricId, payload);
        await this.loadMetrics();
        return {
          importedCount: response.imported_count,
          skippedCount: response.skipped_count,
        };
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to import metric values.";
        return null;
      } finally {
        this.submissionState = "idle";
      }
    },
    async setMetricArchived(metricId: string, archived: boolean): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateMetric(metricId, { archived });
        await this.loadMetrics();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to update metric archive state.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async deleteMetric(metricId: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await deleteMetric(metricId);
        await this.loadMetrics();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to delete metric.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
