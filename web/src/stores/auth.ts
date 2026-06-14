import { defineStore } from "pinia";

import {
  ApiError,
  authMode,
  bootstrapFirstUser,
  changeCurrentPassword,
  deleteCurrentAccount,
  fetchBootstrapStatus,
  fetchCurrentSession,
  buildOAuthLoginUrl,
  loginWithPassword,
  registerWithInvitationCode,
  logoutCurrentSession,
  updateCurrentProfile,
  uploadCurrentAvatar,
  type ChangePasswordPayload,
  type CredentialsPayload,
  type DeleteAccountPayload,
  type RegistrationPayload,
  type UpdateProfilePayload,
  type UserSummary,
} from "../lib/api";

type AuthViewState = "loading" | "guest" | "authenticated";
type AuthSubmissionState = "idle" | "submitting";

const oauthErrorMessages: Record<string, string> = {
  oauth_failed: "Central sign-in could not be completed. Please try again.",
  oauth_state: "Central sign-in expired. Please start again.",
};

type OAuthError = {
  code: string;
  message: string;
};

const oauthAutoRetryKey = "goals.oauth_state_auto_retry";

function consumeOAuthError(): OAuthError | null {
  if (typeof window === "undefined") {
    return null;
  }
  const params = new URLSearchParams(window.location.search);
  const code = params.get("oauth_error");
  if (code === null) {
    return null;
  }

  params.delete("oauth_error");
  const nextSearch = params.toString();
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`,
  );
  return {
    code,
    message: oauthErrorMessages[code] ?? "Central sign-in could not be completed. Please try again.",
  };
}

function claimOAuthStateAutoRetry(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    if (window.sessionStorage.getItem(oauthAutoRetryKey) === "1") {
      return false;
    }
    window.sessionStorage.setItem(oauthAutoRetryKey, "1");
    return true;
  } catch {
    return false;
  }
}

function clearOAuthStateAutoRetry(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.sessionStorage.removeItem(oauthAutoRetryKey);
  } catch {
    // Ignore unavailable session storage.
  }
}

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
      clearOAuthStateAutoRetry();
      this.currentUser = user;
      this.bootstrapRequired = false;
      this.viewState = "authenticated";
    },
    async initialize(): Promise<void> {
      this.viewState = "loading";
      const oauthError = consumeOAuthError();
      this.errorMessage = oauthError?.message ?? "";

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

      if (authMode === "oauth") {
        this.currentUser = null;
        this.bootstrapRequired = false;
        this.viewState = "guest";
        if (oauthError?.code === "oauth_state" && claimOAuthStateAutoRetry()) {
          window.location.assign(buildOAuthLoginUrl());
          return;
        }
        if (oauthError === null && this.errorMessage === "") {
          window.location.assign(buildOAuthLoginUrl());
        }
        return;
      }

      try {
        const bootstrapStatus = await fetchBootstrapStatus();
        this.bootstrapRequired = authMode === "local" && bootstrapStatus.bootstrap_required;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load auth state.";
      }

      this.currentUser = null;
      this.viewState = "guest";
    },
    async bootstrap(credentials: CredentialsPayload): Promise<void> {
      if (authMode === "oauth") {
        window.location.assign(buildOAuthLoginUrl());
        return;
      }
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
      if (authMode === "oauth") {
        window.location.assign(buildOAuthLoginUrl());
        return;
      }
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
    async register(payload: RegistrationPayload): Promise<void> {
      if (authMode === "oauth") {
        window.location.assign(buildOAuthLoginUrl());
        return;
      }
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const session = await registerWithInvitationCode(payload);
        this.applyCurrentUser(session.user);
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to create the account.";
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
