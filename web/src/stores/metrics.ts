import { defineStore } from "pinia";

import {
  addMetricEntry,
  createMetric,
  fetchMetrics,
  type CreateMetricEntryPayload,
  type CreateMetricPayload,
  type MetricSummary,
} from "../lib/api";

type MetricsViewState = "idle" | "loading" | "ready" | "error";
type MetricsSubmissionState = "idle" | "submitting";

interface MetricsStoreState {
  errorMessage: string;
  metrics: MetricSummary[];
  submissionState: MetricsSubmissionState;
  viewState: MetricsViewState;
}

export const useMetricsStore = defineStore("metrics", {
  state: (): MetricsStoreState => ({
    errorMessage: "",
    metrics: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.metrics = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadMetrics(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchMetrics();
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
  },
});
