import { defineStore } from "pinia";

import { fetchStatus, type StatusResponse } from "../lib/api";

type StatusLoadState = "idle" | "loading" | "ready" | "error";

interface StatusStoreState {
  data: StatusResponse | null;
  errorMessage: string;
  state: StatusLoadState;
}

export const useStatusStore = defineStore("status", {
  state: (): StatusStoreState => ({
    data: null,
    errorMessage: "",
    state: "idle",
  }),
  actions: {
    async loadStatus(): Promise<void> {
      this.state = "loading";
      this.errorMessage = "";

      try {
        this.data = await fetchStatus();
        this.state = "ready";
      } catch (error: unknown) {
        this.state = "error";
        this.errorMessage = error instanceof Error ? error.message : "Unable to load application status.";
      }
    },
  },
});
