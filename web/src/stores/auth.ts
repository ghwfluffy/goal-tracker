import { defineStore } from "pinia";

import {
  ApiError,
  bootstrapFirstUser,
  changeCurrentPassword,
  deleteCurrentAccount,
  fetchBootstrapStatus,
  fetchCurrentSession,
  loginWithPassword,
  logoutCurrentSession,
  updateCurrentProfile,
  uploadCurrentAvatar,
  type ChangePasswordPayload,
  type CredentialsPayload,
  type DeleteAccountPayload,
  type UpdateProfilePayload,
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
    applyCurrentUser(user: UserSummary): void {
      this.currentUser = user;
      this.bootstrapRequired = false;
      this.viewState = "authenticated";
    },
    async initialize(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const session = await fetchCurrentSession();
        this.applyCurrentUser(session.user);
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
        this.applyCurrentUser(session.user);
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
        this.applyCurrentUser(session.user);
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
    async updateProfile(payload: UpdateProfilePayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const user = await updateCurrentProfile(payload);
        this.applyCurrentUser(user);
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to update profile details.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async uploadAvatar(file: File): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const user = await uploadCurrentAvatar(file);
        this.applyCurrentUser(user);
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to upload avatar.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async changePassword(payload: ChangePasswordPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const user = await changeCurrentPassword(payload);
        this.applyCurrentUser(user);
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to change password.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async deleteAccount(payload: DeleteAccountPayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await deleteCurrentAccount(payload);
        await this.initialize();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to delete the account.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
