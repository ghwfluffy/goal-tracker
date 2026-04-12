<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Dropdown from "primevue/dropdown";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import { buildApiBaseUrl } from "../../lib/basePath";
import { DEFAULT_PROFILE_TIMEZONE } from "../../lib/time";
import { buildShareLinkUrl, copyCacheBustedShareLink } from "../../lib/shareLinks";
import { formatDateTime } from "../../lib/tracking";
import { useAppToast, watchToastError } from "../../lib/toast";
import { useAuthStore } from "../../stores/auth";
import { useBackupsStore } from "../../stores/backups";
import { useDashboardsStore } from "../../stores/dashboards";
import { useInvitationCodesStore } from "../../stores/invitationCodes";
import { useShareLinksStore } from "../../stores/shareLinks";

const props = defineProps<{
  backupsVisible: boolean;
  deleteAccountVisible: boolean;
  invitationCodesVisible: boolean;
  passwordVisible: boolean;
  profileVisible: boolean;
  sharedLinksVisible: boolean;
}>();

const emit = defineEmits<{
  "update:backupsVisible": [value: boolean];
  "update:deleteAccountVisible": [value: boolean];
  "update:invitationCodesVisible": [value: boolean];
  "update:passwordVisible": [value: boolean];
  "update:profileVisible": [value: boolean];
  "update:sharedLinksVisible": [value: boolean];
}>();

const authStore = useAuthStore();
const backupsStore = useBackupsStore();
const dashboardsStore = useDashboardsStore();
const invitationCodesStore = useInvitationCodesStore();
const shareLinksStore = useShareLinksStore();
const { showError, showSuccess } = useAppToast();
const avatarApiBaseUrl = buildApiBaseUrl(
  import.meta.env.BASE_URL,
  import.meta.env.VITE_API_BASE_URL,
);

const displayNameInput = ref("");
const timezoneInput = ref(DEFAULT_PROFILE_TIMEZONE);
const currentPasswordInput = ref("");
const newPasswordInput = ref("");
const deletePasswordInput = ref("");
const createInvitationCodeExpiresAt = ref("");
const invitationCodeExpiresAtInputs = ref<Record<string, string>>({});
const restoreConfirmationInputs = ref<Record<string, string>>({});
const shareTargetTypeInput = ref<"widget" | "dashboard">("widget");
const shareTargetIdInput = ref("");
const shareExpirationInput = ref<"30_days" | "never">("30_days");

const timezoneOptions = computed(() => {
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: string) => string[];
  };
  const supportedTimezones = intlWithSupportedValues.supportedValuesOf?.(
    "timeZone",
  ) ?? [
    "America/Chicago",
    "America/Los_Angeles",
    "America/New_York",
    "America/Denver",
    "UTC",
  ];
  const currentTimezone =
    authStore.currentUser?.timezone ?? timezoneInput.value;
  return Array.from(
    new Set(
      [currentTimezone, DEFAULT_PROFILE_TIMEZONE, ...supportedTimezones].filter(
        Boolean,
      ),
    ),
  ).sort((left, right) => left.localeCompare(right));
});

const currentDisplayName = computed(() => {
  if (authStore.currentUser === null) {
    return "";
  }

  return authStore.currentUser.display_name || authStore.currentUser.username;
});

const avatarLabel = computed(() => {
  const source = currentDisplayName.value.trim();
  if (source === "") {
    return "GT";
  }

  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
});

const avatarUrl = computed(() => {
  const version = authStore.currentUser?.avatar_version;
  if (version === null || version === undefined) {
    return null;
  }

  return `${avatarApiBaseUrl}/users/me/avatar?v=${encodeURIComponent(version)}`;
});

const shareTargetTypeOptions = [
  { label: "Widget", value: "widget" },
  { label: "Dashboard", value: "dashboard" },
] as const;

const shareExpirationOptions = [
  { label: "30 days", value: "30_days" },
  { label: "Never expires", value: "never" },
] as const;

const widgetShareTargetOptions = computed(() => {
  return dashboardsStore.dashboards.flatMap((dashboard) =>
    dashboard.widgets.map((widget) => ({
      label: `${widget.title} • ${dashboard.name}`,
      value: widget.id,
    })),
  );
});

const dashboardShareTargetOptions = computed(() => {
  return dashboardsStore.dashboards.map((dashboard) => ({
    label: dashboard.name,
    value: dashboard.id,
  }));
});

const activeShareTargetOptions = computed(() => {
  return shareTargetTypeInput.value === "widget"
    ? widgetShareTargetOptions.value
    : dashboardShareTargetOptions.value;
});

function syncProfileInputs(): void {
  displayNameInput.value = authStore.currentUser?.display_name ?? "";
  timezoneInput.value =
    authStore.currentUser?.timezone ?? DEFAULT_PROFILE_TIMEZONE;
}

function resetPasswordInputs(): void {
  currentPasswordInput.value = "";
  newPasswordInput.value = "";
}

function resetDeleteAccountInputs(): void {
  deletePasswordInput.value = "";
}

function toDateTimeLocalValue(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const timezoneOffset = date.getTimezoneOffset();
  return new Date(date.getTime() - timezoneOffset * 60_000)
    .toISOString()
    .slice(0, 16);
}

function defaultInvitationCodeExpiration(): string {
  return toDateTimeLocalValue(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  );
}

function toIsoDateTime(value: string): string | null {
  if (value.trim() === "") {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toISOString();
}

function syncInvitationCodeInputs(): void {
  invitationCodeExpiresAtInputs.value = Object.fromEntries(
    invitationCodesStore.invitationCodes.map((invitationCode) => [
      invitationCode.id,
      toDateTimeLocalValue(invitationCode.expires_at),
    ]),
  );
}

function syncRestoreInputs(): void {
  restoreConfirmationInputs.value = Object.fromEntries(
    backupsStore.backups.map((backup) => [backup.id, ""]),
  );
}

function syncShareTargetInput(): void {
  const widgetOptions = widgetShareTargetOptions.value;
  const dashboardOptions = dashboardShareTargetOptions.value;
  const selectedOptions =
    shareTargetTypeInput.value === "widget" ? widgetOptions : dashboardOptions;

  if (selectedOptions.length === 0) {
    if (shareTargetTypeInput.value === "widget" && dashboardOptions.length > 0) {
      shareTargetTypeInput.value = "dashboard";
      shareTargetIdInput.value = dashboardOptions[0]?.value ?? "";
      return;
    }
    if (shareTargetTypeInput.value === "dashboard" && widgetOptions.length > 0) {
      shareTargetTypeInput.value = "widget";
      shareTargetIdInput.value = widgetOptions[0]?.value ?? "";
      return;
    }
    shareTargetIdInput.value = "";
    return;
  }

  const optionValues = new Set(selectedOptions.map((option) => option.value));
  if (!optionValues.has(shareTargetIdInput.value)) {
    shareTargetIdInput.value = selectedOptions[0]?.value ?? "";
  }
}

function resetShareLinkInputs(): void {
  shareTargetTypeInput.value =
    widgetShareTargetOptions.value.length > 0 ? "widget" : "dashboard";
  shareExpirationInput.value = "30_days";
  syncShareTargetInput();
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

watchToastError(() => invitationCodesStore.errorMessage, "Invitation codes");
watchToastError(() => backupsStore.errorMessage, "Backups");

function shareLinkStatusLabel(status: "active" | "expired" | "revoked"): string {
  if (status === "expired") {
    return "Expired";
  }
  if (status === "revoked") {
    return "Revoked";
  }
  return "Active";
}

function shareLinkStatusSeverity(
  status: "active" | "expired" | "revoked",
): "success" | "warning" | "danger" {
  if (status === "expired") {
    return "warning";
  }
  if (status === "revoked") {
    return "danger";
  }
  return "success";
}

function shareLinkTargetLabel(shareLink: {
  target_type: "dashboard" | "widget";
  widget_type: string | null;
}): string {
  if (shareLink.target_type === "dashboard") {
    return "Dashboard";
  }

  const widgetTypeLabel = shareLink.widget_type
    ?.replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
  return widgetTypeLabel === undefined ? "Widget" : `Widget • ${widgetTypeLabel}`;
}

function shareLinkExpirationText(shareLink: {
  expires_at: string | null;
  revoked_at: string | null;
}): string {
  if (shareLink.revoked_at !== null) {
    return `Revoked ${formatDateTime(shareLink.revoked_at)}`;
  }
  if (shareLink.expires_at === null) {
    return "Never expires";
  }
  return `Expires ${formatDateTime(shareLink.expires_at)}`;
}

async function saveProfile(): Promise<void> {
  const updated = await authStore.updateProfile({
    display_name:
      displayNameInput.value.trim() === "" ? null : displayNameInput.value,
    timezone: timezoneInput.value.trim() === "" ? null : timezoneInput.value,
  });

  if (updated) {
    showSuccess("Profile updated.", "Profile");
  }
}

async function changePassword(): Promise<void> {
  const updated = await authStore.changePassword({
    current_password: currentPasswordInput.value,
    new_password: newPasswordInput.value,
  });

  if (updated) {
    showSuccess("Password changed.", "Profile");
    resetPasswordInputs();
  }
}

async function uploadAvatar(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file === undefined) {
    return;
  }

  const uploaded = await authStore.uploadAvatar(file);
  if (uploaded) {
    showSuccess("Avatar updated.", "Profile");
  }

  input.value = "";
}

async function deleteAccount(): Promise<void> {
  const deleted = await authStore.deleteAccount({
    password: deletePasswordInput.value,
  });

  if (deleted) {
    showSuccess("Account deleted.", "Profile");
    emit("update:deleteAccountVisible", false);
  }
}

async function createNewInvitationCode(): Promise<void> {
  const expiresAt = toIsoDateTime(createInvitationCodeExpiresAt.value);
  if (expiresAt === null) {
    showError("Choose a valid expiration date.", "Invitation codes");
    return;
  }

  const created = await invitationCodesStore.createInvitationCode({
    expires_at: expiresAt,
  });
  syncInvitationCodeInputs();

  if (created) {
    showSuccess("Invitation code created.", "Invitation codes");
    createInvitationCodeExpiresAt.value = defaultInvitationCodeExpiration();
  }
}

async function saveInvitationCode(invitationCodeId: string): Promise<void> {
  const expiresAt = toIsoDateTime(
    invitationCodeExpiresAtInputs.value[invitationCodeId] ?? "",
  );
  if (expiresAt === null) {
    showError("Choose a valid expiration date.", "Invitation codes");
    return;
  }

  const updated = await invitationCodesStore.updateInvitationCode(
    invitationCodeId,
    {
      expires_at: expiresAt,
    },
  );
  syncInvitationCodeInputs();

  if (updated) {
    showSuccess("Invitation code updated.", "Invitation codes");
  }
}

async function deleteInvitationCodeEntry(
  invitationCodeId: string,
): Promise<void> {
  const deleted =
    await invitationCodesStore.deleteInvitationCode(invitationCodeId);
  syncInvitationCodeInputs();

  if (deleted) {
    showSuccess("Invitation code deleted.", "Invitation codes");
  }
}

async function createManualBackup(): Promise<void> {
  const created = await backupsStore.createBackup();
  syncRestoreInputs();

  if (created) {
    showSuccess("Backup created.", "Backups");
  }
}

async function restoreBackupEntry(backupId: string): Promise<void> {
  const restored = await backupsStore.restoreBackup(
    backupId,
    restoreConfirmationInputs.value[backupId] ?? "",
  );
  syncRestoreInputs();

  if (restored) {
    showSuccess("Backup restored.", "Backups");
  }
}

async function createNewShareLink(): Promise<void> {
  if (shareTargetIdInput.value === "") {
    showError("Choose a dashboard or widget to share.", "Shared links");
    return;
  }

  const createdShareLink = await shareLinksStore.createShareLink({
    expires_in_days: shareExpirationInput.value === "never" ? null : 30,
    target_id: shareTargetIdInput.value,
    target_type: shareTargetTypeInput.value,
  });

  if (createdShareLink === null) {
    return;
  }

  try {
    await copyCacheBustedShareLink(
      createdShareLink.public_path,
      window.location.origin,
    );
    showSuccess("Share link copied.", "Shared links");
  } catch {
    showError(
      "Share link was created, but clipboard access failed. Use the copy button below.",
      "Shared links",
    );
  }
}

async function copyShareLinkEntry(publicPath: string): Promise<void> {
  try {
    await copyCacheBustedShareLink(publicPath, window.location.origin);
    showSuccess("Share link copied.", "Shared links");
  } catch {
    showError("Clipboard access failed.", "Shared links");
  }
}

function openShareLinkEntry(publicPath: string): void {
  window.open(
    buildShareLinkUrl(publicPath, window.location.origin),
    "_blank",
    "noopener,noreferrer",
  );
}

async function revokeShareLinkEntry(shareLinkId: string): Promise<void> {
  const revoked = await shareLinksStore.revokeShareLink(shareLinkId);
  if (revoked) {
    showSuccess("Share link revoked.", "Shared links");
  }
}

watch(
  () => authStore.currentUser,
  () => {
    syncProfileInputs();
    resetPasswordInputs();
    resetDeleteAccountInputs();
  },
  { immediate: true },
);

watch(
  () => invitationCodesStore.invitationCodes,
  () => {
    syncInvitationCodeInputs();
  },
  { deep: true },
);

watch(
  () => backupsStore.backups,
  () => {
    syncRestoreInputs();
  },
  { deep: true },
);

watch(
  () => dashboardsStore.dashboards,
  () => {
    syncShareTargetInput();
  },
  { deep: true, immediate: true },
);

watch(
  () => shareTargetTypeInput.value,
  () => {
    syncShareTargetInput();
  },
);

watch(
  () => props.invitationCodesVisible,
  async (visible) => {
    if (!visible) {
      return;
    }
    createInvitationCodeExpiresAt.value = defaultInvitationCodeExpiration();
    await invitationCodesStore.loadInvitationCodes();
    syncInvitationCodeInputs();
  },
);

watch(
  () => props.backupsVisible,
  async (visible) => {
    if (!visible) {
      return;
    }
    await backupsStore.loadBackupInventory();
    syncRestoreInputs();
  },
);

watch(
  () => props.sharedLinksVisible,
  async (visible) => {
    if (!visible) {
      return;
    }
    resetShareLinkInputs();
    await shareLinksStore.loadShareLinks();
  },
);
</script>

<template>
  <Dialog
    :visible="profileVisible"
    modal
    header="Edit profile"
    class="profile-dialog"
    :style="{ width: 'min(44rem, 96vw)' }"
    @update:visible="(value) => emit('update:profileVisible', value)"
  >
    <div class="dialog-stack">
      <section class="dialog-section">
        <div class="section-heading">
          <Avatar
            :image="avatarUrl ?? undefined"
            :label="avatarUrl === null ? avatarLabel : undefined"
            shape="circle"
            size="xlarge"
          />
          <div>
            <h3>Profile details</h3>
            <p>Update the name shown in the header and upload a new avatar.</p>
          </div>
        </div>

        <label class="field">
          <span class="label">Display name</span>
          <InputText v-model="displayNameInput" />
        </label>

        <label class="field">
          <span class="label">Day boundary timezone</span>
          <Dropdown
            v-model="timezoneInput"
            :options="timezoneOptions"
            class="full-width-dropdown"
            filter
            placeholder="Select timezone"
          />
        </label>

        <p class="dialog-copy">
          Timestamps render in your browser timezone. This profile timezone
          controls how the app should interpret day boundaries for tracking
          logic.
        </p>

        <label class="field">
          <span class="label">Avatar image</span>
          <input
            class="native-file-input"
            type="file"
            accept="image/*"
            @change="uploadAvatar"
          />
        </label>

        <Button
          label="Save profile"
          icon="pi pi-save"
          :loading="authStore.submissionState === 'submitting'"
          @click="saveProfile"
        />
      </section>
    </div>
  </Dialog>

  <Dialog
    :visible="passwordVisible"
    modal
    header="Change password"
    class="profile-dialog"
    :style="{ width: 'min(32rem, 96vw)' }"
    @update:visible="(value) => emit('update:passwordVisible', value)"
  >
    <div class="dialog-stack">
      <section class="dialog-section">
        <div class="section-heading-text">
          <h3>Change password</h3>
          <p>Use your current password to set a new one.</p>
        </div>

        <label class="field">
          <span class="label">Current password</span>
          <Password
            v-model="currentPasswordInput"
            input-class="full-width-input"
            :feedback="false"
            toggle-mask
          />
        </label>

        <label class="field">
          <span class="label">New password</span>
          <Password
            v-model="newPasswordInput"
            input-class="full-width-input"
            :feedback="false"
            toggle-mask
          />
        </label>

        <Button
          label="Change password"
          icon="pi pi-key"
          severity="secondary"
          :loading="authStore.submissionState === 'submitting'"
          @click="changePassword"
        />
      </section>
    </div>
  </Dialog>

  <Dialog
    :visible="deleteAccountVisible"
    modal
    header="Delete account"
    class="profile-dialog"
    :style="{ width: 'min(32rem, 96vw)' }"
    @update:visible="(value) => emit('update:deleteAccountVisible', value)"
  >
    <div class="dialog-stack">
      <section class="dialog-section danger-section">
        <div class="section-heading-text">
          <h3>Delete account</h3>
          <p>This permanently removes your account and current session.</p>
        </div>

        <label class="field">
          <span class="label">Confirm with password</span>
          <Password
            v-model="deletePasswordInput"
            input-class="full-width-input"
            :feedback="false"
            toggle-mask
          />
        </label>

        <Button
          label="Delete account"
          icon="pi pi-trash"
          severity="danger"
          :loading="authStore.submissionState === 'submitting'"
          @click="deleteAccount"
        />
      </section>
    </div>
  </Dialog>

  <Dialog
    :visible="backupsVisible"
    modal
    header="Backups"
    class="profile-dialog"
    :style="{ width: 'min(64rem, 96vw)' }"
    @update:visible="(value) => emit('update:backupsVisible', value)"
  >
    <div class="dialog-stack">
      <div
        v-if="backupsStore.viewState === 'loading'"
        class="loading shell-center"
      >
        <ProgressSpinner
          strokeWidth="5"
          style="width: 2.5rem; height: 2.5rem"
          animationDuration=".8s"
        />
        <span>Loading backups.</span>
      </div>

      <template v-else>
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Create backup</h3>
            <p>
              Manual backups write into the repository `./backups` directory.
              Restore takes a fresh pre-restore backup before replacing the
              database contents.
            </p>
          </div>

          <Button
            label="Create backup"
            icon="pi pi-download"
            :loading="backupsStore.submissionState === 'submitting'"
            @click="createManualBackup"
          />
        </section>

        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Available backups</h3>
            <p>
              Automatic and manual backups are both listed here. Restore
              requires typing `RESTORE`.
            </p>
          </div>

          <div
            v-if="backupsStore.backups.length === 0"
            class="panel-card empty-invitation-state"
          >
            <p>No backups yet.</p>
          </div>

          <article
            v-for="backup in backupsStore.backups"
            :key="backup.id"
            class="invitation-code-card"
          >
            <div class="invitation-code-header">
              <div class="invitation-code-copy">
                <p class="code-label">{{ backup.trigger_source }}</p>
                <code>{{ backup.filename }}</code>
              </div>
              <Tag :value="backup.trigger_source" severity="info" />
            </div>

            <div class="invitation-code-meta">
              <span>Created {{ formatDateTime(backup.created_at) }}</span>
              <span>Size {{ formatFileSize(backup.file_size_bytes) }}</span>
              <span v-if="backup.created_by_user !== null">
                By
                {{
                  backup.created_by_user.display_name ??
                  backup.created_by_user.username
                }}
              </span>
            </div>

            <div class="invitation-code-actions">
              <label class="field">
                <span class="label">Confirm restore</span>
                <InputText
                  v-model="restoreConfirmationInputs[backup.id]"
                  placeholder="Type RESTORE"
                />
              </label>

              <div class="invitation-code-buttons">
                <Button
                  label="Restore"
                  icon="pi pi-history"
                  severity="danger"
                  :loading="backupsStore.submissionState === 'submitting'"
                  @click="restoreBackupEntry(backup.id)"
                />
              </div>
            </div>
          </article>
        </section>

        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Recent restores</h3>
            <p>Completed restores and any reported failures are shown here.</p>
          </div>

          <div
            v-if="backupsStore.restores.length === 0"
            class="panel-card empty-invitation-state"
          >
            <p>No restore operations yet.</p>
          </div>

          <article
            v-for="restore in backupsStore.restores"
            :key="restore.id"
            class="invitation-code-card"
          >
            <div class="invitation-code-header">
              <div class="invitation-code-copy">
                <p class="code-label">Restore</p>
                <code>{{ restore.backup?.filename ?? "Unknown backup" }}</code>
              </div>
              <Tag
                :value="restore.status"
                :severity="
                  restore.status === 'completed' ? 'success' : 'danger'
                "
              />
            </div>

            <div class="invitation-code-meta">
              <span>Requested {{ formatDateTime(restore.requested_at) }}</span>
              <span v-if="restore.completed_at !== null">
                Completed {{ formatDateTime(restore.completed_at) }}
              </span>
              <span v-if="restore.requested_by_user !== null">
                By
                {{
                  restore.requested_by_user.display_name ??
                  restore.requested_by_user.username
                }}
              </span>
            </div>

            <p v-if="restore.error_message !== null" class="dialog-copy">
              {{ restore.error_message }}
            </p>
            <p
              v-else-if="restore.pre_restore_backup !== null"
              class="dialog-copy"
            >
              Pre-restore safety backup:
              {{ restore.pre_restore_backup.filename }}
            </p>
          </article>
        </section>
      </template>
    </div>
  </Dialog>

  <Dialog
    :visible="sharedLinksVisible"
    modal
    header="Shared links"
    class="profile-dialog"
    :style="{ width: 'min(64rem, 96vw)' }"
    @update:visible="(value) => emit('update:sharedLinksVisible', value)"
  >
    <div class="dialog-stack">
      <div
        v-if="shareLinksStore.viewState === 'loading'"
        class="loading shell-center"
      >
        <ProgressSpinner
          strokeWidth="5"
          style="width: 2.5rem; height: 2.5rem"
          animationDuration=".8s"
        />
        <span>Loading share links.</span>
      </div>

      <template v-else>
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Create share link</h3>
            <p>
              Links default to 30 days, can be unlimited, and copy with an
              unused `?t=` cache-busting suffix for fresh embeds.
            </p>
          </div>

          <div class="invitation-code-actions shared-link-create-grid">
            <label class="field">
              <span class="label">Target type</span>
              <Dropdown
                v-model="shareTargetTypeInput"
                :options="shareTargetTypeOptions"
                option-label="label"
                option-value="value"
                class="full-width-dropdown"
              />
            </label>

            <label class="field">
              <span class="label">Target</span>
              <Dropdown
                v-model="shareTargetIdInput"
                :options="activeShareTargetOptions"
                option-label="label"
                option-value="value"
                class="full-width-dropdown"
                placeholder="Choose a target"
                :disabled="activeShareTargetOptions.length === 0"
              />
            </label>

            <label class="field">
              <span class="label">Expiration</span>
              <Dropdown
                v-model="shareExpirationInput"
                :options="shareExpirationOptions"
                option-label="label"
                option-value="value"
                class="full-width-dropdown"
              />
            </label>

            <div class="invitation-code-buttons">
              <Button
                label="Create and copy link"
                icon="pi pi-copy"
                :disabled="shareTargetIdInput === ''"
                :loading="shareLinksStore.submissionState === 'submitting'"
                @click="createNewShareLink"
              />
            </div>
          </div>
        </section>

        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Managed links</h3>
            <p>
              Revoke links centrally here and copy fresh URLs whenever Discord,
              Teams, or other previews need to refresh.
            </p>
          </div>

          <div
            v-if="shareLinksStore.shareLinks.length === 0"
            class="panel-card empty-invitation-state"
          >
            <p>No share links yet.</p>
          </div>

          <article
            v-for="shareLink in shareLinksStore.shareLinks"
            :key="shareLink.id"
            class="invitation-code-card"
          >
            <div class="invitation-code-header">
              <div class="invitation-code-copy">
                <p class="code-label">
                  {{ shareLinkTargetLabel(shareLink) }}
                </p>
                <code>{{ shareLink.public_path }}</code>
              </div>
              <Tag
                :value="shareLinkStatusLabel(shareLink.status)"
                :severity="shareLinkStatusSeverity(shareLink.status)"
              />
            </div>

            <div class="invitation-code-meta">
              <span>{{ shareLink.target_name }}</span>
              <span v-if="shareLink.dashboard_name !== null">
                Dashboard {{ shareLink.dashboard_name }}
              </span>
              <span>Created {{ formatDateTime(shareLink.created_at) }}</span>
              <span>{{ shareLinkExpirationText(shareLink) }}</span>
            </div>

            <div class="invitation-code-buttons">
              <Button
                label="Copy link"
                icon="pi pi-copy"
                severity="secondary"
                :disabled="shareLink.status !== 'active'"
                @click="void copyShareLinkEntry(shareLink.public_path)"
              />
              <Button
                label="Open"
                icon="pi pi-external-link"
                severity="secondary"
                outlined
                :disabled="shareLink.status !== 'active'"
                @click="openShareLinkEntry(shareLink.public_path)"
              />
              <Button
                label="Revoke"
                icon="pi pi-ban"
                severity="danger"
                :disabled="shareLink.status !== 'active'"
                :loading="shareLinksStore.submissionState === 'submitting'"
                @click="void revokeShareLinkEntry(shareLink.id)"
              />
            </div>
          </article>
        </section>
      </template>
    </div>
  </Dialog>

  <Dialog
    :visible="invitationCodesVisible"
    modal
    header="Invitation codes"
    class="profile-dialog"
    :style="{ width: 'min(56rem, 96vw)' }"
    @update:visible="(value) => emit('update:invitationCodesVisible', value)"
  >
    <div class="dialog-stack">
      <div
        v-if="invitationCodesStore.viewState === 'loading'"
        class="loading shell-center"
      >
        <ProgressSpinner
          strokeWidth="5"
          style="width: 2.5rem; height: 2.5rem"
          animationDuration=".8s"
        />
        <span>Loading invitation codes.</span>
      </div>

      <template v-else>
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Create invitation code</h3>
            <p>
              New accounts can sign up with any active code until it expires or
              you delete it.
            </p>
          </div>

          <label class="field">
            <span class="label">Expiration</span>
            <input
              v-model="createInvitationCodeExpiresAt"
              class="native-file-input"
              type="datetime-local"
            />
          </label>

          <Button
            label="Create code"
            icon="pi pi-plus"
            :loading="invitationCodesStore.submissionState === 'submitting'"
            @click="createNewInvitationCode"
          />
        </section>

        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Existing codes</h3>
            <p>
              Review expiration, delete old codes, and see which accounts came
              from each one.
            </p>
          </div>

          <div
            v-if="invitationCodesStore.invitationCodes.length === 0"
            class="panel-card empty-invitation-state"
          >
            <p>No invitation codes yet.</p>
          </div>

          <article
            v-for="invitationCode in invitationCodesStore.invitationCodes"
            :key="invitationCode.id"
            class="invitation-code-card"
          >
            <div class="invitation-code-header">
              <div class="invitation-code-copy">
                <p class="code-label">Code</p>
                <code>{{ invitationCode.code }}</code>
              </div>
              <Tag value="active" severity="success" />
            </div>

            <div class="invitation-code-meta">
              <span
                >Created {{ formatDateTime(invitationCode.created_at) }}</span
              >
              <span
                >Expires {{ formatDateTime(invitationCode.expires_at) }}</span
              >
              <span v-if="invitationCode.created_by_username !== null">
                By {{ invitationCode.created_by_username }}
              </span>
            </div>

            <div class="invitation-code-actions">
              <label class="field">
                <span class="label">Update expiration</span>
                <input
                  v-model="invitationCodeExpiresAtInputs[invitationCode.id]"
                  class="native-file-input"
                  type="datetime-local"
                />
              </label>

              <div class="invitation-code-buttons">
                <Button
                  label="Save"
                  icon="pi pi-save"
                  severity="secondary"
                  :loading="
                    invitationCodesStore.submissionState === 'submitting'
                  "
                  @click="saveInvitationCode(invitationCode.id)"
                />
                <Button
                  label="Delete"
                  icon="pi pi-trash"
                  severity="danger"
                  :loading="
                    invitationCodesStore.submissionState === 'submitting'
                  "
                  @click="deleteInvitationCodeEntry(invitationCode.id)"
                />
              </div>
            </div>

            <div class="invitation-code-users">
              <p class="label">Users created with this code</p>
              <div
                v-if="invitationCode.users_created.length === 0"
                class="invitation-code-empty"
              >
                None yet.
              </div>
              <div v-else class="invitation-code-user-list">
                <div
                  v-for="user in invitationCode.users_created"
                  :key="user.id"
                  class="invitation-code-user"
                >
                  <strong>{{ user.display_name || user.username }}</strong>
                  <span>@{{ user.username }}</span>
                  <Tag
                    v-if="user.is_example_data"
                    value="example data"
                    severity="warning"
                  />
                </div>
              </div>
            </div>
          </article>
        </section>
      </template>
    </div>
  </Dialog>
</template>

<style scoped>
.invitation-code-actions,
.shared-link-create-grid,
.invitation-code-users,
.invitation-code-user-list {
  display: grid;
  gap: var(--space-4);
}

.profile-dialog :deep(.p-dialog-content) {
  padding-top: 0.25rem;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.dialog-copy {
  margin: 0;
  line-height: var(--line-height-copy);
  color: var(--color-text-muted);
}

.danger-section {
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: var(--color-surface-danger-soft);
}

.loading {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.empty-invitation-state {
  color: var(--color-text-faint);
}

.invitation-code-card {
  display: grid;
  gap: var(--space-6);
  padding: var(--space-7);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-panel);
  background: var(--color-surface-card-soft);
}

.invitation-code-header,
.invitation-code-meta,
.invitation-code-buttons,
.invitation-code-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.invitation-code-header {
  align-items: flex-start;
}

.invitation-code-copy {
  display: grid;
  gap: var(--space-2);
}

.code-label {
  margin: 0;
  font-size: var(--font-size-caption);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-faint);
}

.invitation-code-copy code {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.95rem;
  word-break: break-all;
  color: var(--color-text-strong);
}

.invitation-code-meta {
  flex-wrap: wrap;
  justify-content: flex-start;
  color: var(--color-text-subtle);
  font-size: var(--font-size-body-sm);
}

.invitation-code-empty {
  color: var(--color-text-faint);
}

.invitation-code-user-list {
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
}

.shared-link-create-grid {
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
}

.invitation-code-user {
  justify-content: flex-start;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-input);
  border: 1px solid var(--color-border-panel-faint);
}

.profile-dialog :deep(.full-width-input),
.profile-dialog :deep(.full-width-dropdown) {
  width: 100%;
}

.profile-dialog :deep(.p-password),
.profile-dialog :deep(.p-dropdown) {
  width: 100%;
}

@media (max-width: 720px) {
  .profile-dialog :deep(.p-dialog) {
    width: calc(100vw - 1rem) !important;
    max-height: calc(100dvh - 1rem);
    margin: 0.5rem;
  }

  .profile-dialog :deep(.p-dialog-header) {
    padding: var(--space-5);
    align-items: flex-start;
  }

  .profile-dialog :deep(.p-dialog-header-icons) {
    margin-left: auto;
  }

  .profile-dialog :deep(.p-dialog-content) {
    padding: 0 var(--space-5) var(--space-5);
    overflow-y: auto;
  }

  .dialog-stack,
  .dialog-section,
  .field {
    gap: var(--space-5);
  }

  .section-heading {
    align-items: flex-start;
    gap: var(--space-4);
  }

  .profile-dialog :deep(.p-button) {
    width: 100%;
  }

  .invitation-code-header,
  .invitation-code-buttons,
  .invitation-code-user {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
