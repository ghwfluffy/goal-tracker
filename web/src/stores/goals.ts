import { defineStore } from "pinia";

import {
  createGoal,
  fetchGoals,
  updateGoal,
  type CreateGoalPayload,
  type GoalSummary,
  type UpdateGoalPayload,
} from "../lib/api";

type GoalsViewState = "idle" | "loading" | "ready" | "error";
type GoalsSubmissionState = "idle" | "submitting";

interface GoalsStoreState {
  errorMessage: string;
  includeArchived: boolean;
  goals: GoalSummary[];
  submissionState: GoalsSubmissionState;
  viewState: GoalsViewState;
}

export const useGoalsStore = defineStore("goals", {
  state: (): GoalsStoreState => ({
    errorMessage: "",
    includeArchived: false,
    goals: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.includeArchived = false;
      this.goals = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadGoals(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchGoals(this.includeArchived);
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
    async updateGoalDetails(goalId: string, payload: UpdateGoalPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateGoal(goalId, payload);
        await this.loadGoals();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to update goal.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async setGoalArchived(goalId: string, archived: boolean): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateGoal(goalId, { archived });
        await this.loadGoals();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to update goal archive state.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
