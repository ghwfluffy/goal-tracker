import { defineStore } from "pinia";

import {
  completeNotification,
  fetchNotifications,
  skipNotification,
  type CompleteNotificationPayload,
  type NotificationSummary,
} from "../lib/api";

type NotificationsViewState = "idle" | "loading" | "ready" | "error";
type NotificationsSubmissionState = "idle" | "submitting";

interface NotificationsStoreState {
  errorMessage: string;
  notifications: NotificationSummary[];
  submissionState: NotificationsSubmissionState;
  viewState: NotificationsViewState;
}

export const useNotificationsStore = defineStore("notifications", {
  state: (): NotificationsStoreState => ({
    errorMessage: "",
    notifications: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  getters: {
    count: (state) => state.notifications.length,
  },
  actions: {
    reset(): void {
      this.errorMessage = "";
      this.notifications = [];
      this.submissionState = "idle";
      this.viewState = "idle";
    },
    async loadNotifications(timezone: string): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const response = await fetchNotifications(timezone);
        this.notifications = response.notifications;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to load notifications.";
        this.viewState = "error";
      }
    },
    async completeNotification(
      notificationId: string,
      payload: CompleteNotificationPayload,
      timezone: string,
    ): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await completeNotification(notificationId, payload);
        await this.loadNotifications(timezone);
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to complete notification.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async skipNotification(notificationId: string, timezone: string): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await skipNotification(notificationId);
        await this.loadNotifications(timezone);
        return true;
      } catch (error: unknown) {
        this.errorMessage = error instanceof Error ? error.message : "Unable to skip notification.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
