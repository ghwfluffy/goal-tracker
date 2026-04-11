import { defineStore } from "pinia";

import {
  createInvitationCode,
  deleteInvitationCode,
  fetchInvitationCodes,
  updateInvitationCode,
  type InvitationCodePayload,
  type InvitationCodeSummary,
} from "../lib/api";

type InvitationCodesViewState = "idle" | "loading" | "ready" | "error";
type InvitationCodesSubmissionState = "idle" | "submitting";

interface InvitationCodesStoreState {
  errorMessage: string;
  invitationCodes: InvitationCodeSummary[];
  submissionState: InvitationCodesSubmissionState;
  viewState: InvitationCodesViewState;
}

export const useInvitationCodesStore = defineStore("invitationCodes", {
  state: (): InvitationCodesStoreState => ({
    errorMessage: "",
    invitationCodes: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    async loadInvitationCodes(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchInvitationCodes();
        this.invitationCodes = response.invitation_codes;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to load invitation codes.";
        this.viewState = "error";
      }
    },
    async createInvitationCode(payload: InvitationCodePayload): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await createInvitationCode(payload);
        await this.loadInvitationCodes();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to create invitation code.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async updateInvitationCode(
      invitationCodeId: string,
      payload: InvitationCodePayload,
    ): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await updateInvitationCode(invitationCodeId, payload);
        await this.loadInvitationCodes();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to update invitation code.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async deleteInvitationCode(invitationCodeId: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await deleteInvitationCode(invitationCodeId);
        await this.loadInvitationCodes();
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to delete invitation code.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
