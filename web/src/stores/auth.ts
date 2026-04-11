import { defineStore } from "pinia";

import {
  ApiError,
  bootstrapFirstUser,
  fetchBootstrapStatus,
  fetchCurrentSession,
  loginWithPassword,
  logoutCurrentSession,
  type CredentialsPayload,
  type UserSummary,
} from "../lib/api";

type AuthViewState = "loading" | "guest" | "authenticated";
type AuthSubmissionState = "idle" | "submitting";

interface AuthStoreState {
  bootstrapRequired: boolean;
  currentUser: UserSummary | null;
  errorMessage: string;
  submissionState: AuthSubmissionState;
  viewState: AuthViewState;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthStoreState => ({
    bootstrapRequired: false,
    currentUser: null,
    errorMessage: "",
    submissionState: "idle",
    viewState: "loading",
  }),
  getters: {
    isAuthenticated: (state) => state.currentUser !== null,
  },
  actions: {
    async initialize(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const session = await fetchCurrentSession();
        this.currentUser = session.user;
        this.bootstrapRequired = false;
        this.viewState = "authenticated";
        return;
      } catch (error: unknown) {
        if (!(error instanceof ApiError) || error.status !== 401) {
          this.errorMessage =
            error instanceof Error ? error.message : "Unable to restore the current session.";
        }
      }

      try {
        const bootstrapStatus = await fetchBootstrapStatus();
        this.bootstrapRequired = bootstrapStatus.bootstrap_required;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load auth state.";
      }

      this.currentUser = null;
      this.viewState = "guest";
    },
    async bootstrap(credentials: CredentialsPayload): Promise<void> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const session = await bootstrapFirstUser(credentials);
        this.currentUser = session.user;
        this.bootstrapRequired = false;
        this.viewState = "authenticated";
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to create the first account.";
      } finally {
        this.submissionState = "idle";
      }
    },
    async login(credentials: CredentialsPayload): Promise<void> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const session = await loginWithPassword(credentials);
        this.currentUser = session.user;
        this.viewState = "authenticated";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to sign in.";
      } finally {
        this.submissionState = "idle";
      }
    },
    async logout(): Promise<void> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await logoutCurrentSession();
        this.currentUser = null;
        this.bootstrapRequired = false;
        this.viewState = "guest";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to sign out.";
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
