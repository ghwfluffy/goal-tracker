import { defineStore } from "pinia";

import {
  createGoal,
  fetchGoals,
  type CreateGoalPayload,
  type GoalSummary,
} from "../lib/api";

type GoalsViewState = "idle" | "loading" | "ready" | "error";
type GoalsSubmissionState = "idle" | "submitting";

interface GoalsStoreState {
  errorMessage: string;
  goals: GoalSummary[];
  submissionState: GoalsSubmissionState;
  viewState: GoalsViewState;
}

export const useGoalsStore = defineStore("goals", {
  state: (): GoalsStoreState => ({
    errorMessage: "",
    goals: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.goals = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadGoals(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchGoals();
        this.goals = response.goals;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load goals.";
        this.viewState = "error";
      }
    },
    async createGoal(payload: CreateGoalPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await createGoal(payload);
        await this.loadGoals();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to create goal.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
