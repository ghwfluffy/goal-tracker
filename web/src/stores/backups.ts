import { defineStore } from "pinia";

import {
  createBackup,
  fetchBackupInventory,
  restoreBackup,
  type BackupSummary,
  type RestoreOperationSummary,
} from "../lib/api";

type BackupsViewState = "idle" | "loading" | "ready" | "error";
type BackupsSubmissionState = "idle" | "submitting";

interface BackupsStoreState {
  backups: BackupSummary[];
  errorMessage: string;
  restores: RestoreOperationSummary[];
  submissionState: BackupsSubmissionState;
  viewState: BackupsViewState;
}

export const useBackupsStore = defineStore("backups", {
  state: (): BackupsStoreState => ({
    backups: [],
    errorMessage: "",
    restores: [],
    submissionState: "idle",
    viewState: "idle",
  }),
  actions: {
    async loadBackupInventory(): Promise<void> {
      this.viewState = "loading";
      this.errorMessage = "";

      try {
        const inventory = await fetchBackupInventory();
        this.backups = inventory.backups;
        this.restores = inventory.restores;
        this.viewState = "ready";
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error
            ? error.message
            : "Unable to load backup inventory.";
        this.viewState = "error";
      }
    },
    async createBackup(): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await createBackup();
        await this.loadBackupInventory();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error ? error.message : "Unable to create a backup.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
    async restoreBackup(
      backupId: string,
      confirmationText: string,
    ): Promise<boolean> {
      this.submissionState = "submitting";
      this.errorMessage = "";

      try {
        await restoreBackup(backupId, { confirmation_text: confirmationText });
        await this.loadBackupInventory();
        return true;
      } catch (error: unknown) {
        this.errorMessage =
          error instanceof Error
            ? error.message
            : "Unable to restore the backup.";
        return false;
      } finally {
        this.submissionState = "idle";
      }
    },
  },
});
