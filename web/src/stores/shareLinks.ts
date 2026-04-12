import { defineStore } from "pinia";

import {
  createShareLink as createShareLinkRequest,
  fetchShareLinks as fetchShareLinksRequest,
  revokeShareLink as revokeShareLinkRequest,
  type CreateShareLinkPayload,
  type ShareLinkSummary,
} from "../lib/api";

type ShareLinksViewState = "idle" | "loading" | "ready" | "error";
type ShareLinksSubmissionState = "idle" | "submitting";

interface ShareLinksStoreState {
  errorMessage: string;
  shareLinks: ShareLinkSummary[];
  submissionState: ShareLinksSubmissionState;
  viewState: ShareLinksViewState;
}

export const useShareLinksStore = defineStore("shareLinks", {
  state: (): ShareLinksStoreState => ({
    errorMessage: "",
    shareLinks: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.shareLinks = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadShareLinks(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchShareLinksRequest();
        this.shareLinks = response.share_links;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to load share links.";
        this.viewState = "error";
      }
    },
    async createShareLink(
      payload: CreateShareLinkPayload,
    ): Promise<ShareLinkSummary | null> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        const createdShareLink = await createShareLinkRequest(payload);
        this.shareLinks = [
          createdShareLink,
          ...this.shareLinks.filter(
            (shareLink) => shareLink.id !== createdShareLink.id,
          ),
        ];
        this.viewState = "ready";
        return createdShareLink;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to create share link.";
        return null;
      } finally {
        this.submissionState = "idle";
      }
    },
    async revokeShareLink(shareLinkId: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await revokeShareLinkRequest(shareLinkId);
        await this.loadShareLinks();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to revoke share link.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
