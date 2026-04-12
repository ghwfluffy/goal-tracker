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

import { DEFAULT_PROFILE_TIMEZONE } from "../../lib/time";
import { formatDateTime } from "../../lib/tracking";
import { useAppToast, watchToastError } from "../../lib/toast";
import { useAuthStore } from "../../stores/auth";
import { useInvitationCodesStore } from "../../stores/invitationCodes";

const props = defineProps<{
  deleteAccountVisible: boolean;
  invitationCodesVisible: boolean;
  passwordVisible: boolean;
  profileVisible: boolean;
}>();

const emit = defineEmits<{
  "update:deleteAccountVisible": [value: boolean];
  "update:invitationCodesVisible": [value: boolean];
  "update:passwordVisible": [value: boolean];
  "update:profileVisible": [value: boolean];
}>();

const authStore = useAuthStore();
const invitationCodesStore = useInvitationCodesStore();
const { showError, showSuccess } = useAppToast();

const displayNameInput = ref("");
const timezoneInput = ref(DEFAULT_PROFILE_TIMEZONE);
const currentPasswordInput = ref("");
const newPasswordInput = ref("");
const deletePasswordInput = ref("");
const createInvitationCodeExpiresAt = ref("");
const invitationCodeExpiresAtInputs = ref<Record<string, string>>({});

const timezoneOptions = computed(() => {
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: string) => string[];
  };
  const supportedTimezones = intlWithSupportedValues.supportedValuesOf?.("timeZone") ?? [
    "America/Chicago",
    "America/Los_Angeles",
    "America/New_York",
    "America/Denver",
    "UTC",
  ];
  const currentTimezone = authStore.currentUser?.timezone ?? timezoneInput.value;
  return Array.from(
    new Set([currentTimezone, DEFAULT_PROFILE_TIMEZONE, ...supportedTimezones].filter(Boolean)),
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

  return `/api/v1/users/me/avatar?v=${encodeURIComponent(version)}`;
});

function syncProfileInputs(): void {
  displayNameInput.value = authStore.currentUser?.display_name ?? "";
  timezoneInput.value = authStore.currentUser?.timezone ?? DEFAULT_PROFILE_TIMEZONE;
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
  return new Date(date.getTime() - timezoneOffset * 60_000).toISOString().slice(0, 16);
}

function defaultInvitationCodeExpiration(): string {
  return toDateTimeLocalValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString());
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

watchToastError(() => invitationCodesStore.errorMessage, "Invitation codes");

async function saveProfile(): Promise<void> {
  const updated = await authStore.updateProfile({
    display_name: displayNameInput.value.trim() === "" ? null : displayNameInput.value,
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

  const created = await invitationCodesStore.createInvitationCode({ expires_at: expiresAt });
  syncInvitationCodeInputs();

  if (created) {
    showSuccess("Invitation code created.", "Invitation codes");
    createInvitationCodeExpiresAt.value = defaultInvitationCodeExpiration();
  }
}

async function saveInvitationCode(invitationCodeId: string): Promise<void> {
  const expiresAt = toIsoDateTime(invitationCodeExpiresAtInputs.value[invitationCodeId] ?? "");
  if (expiresAt === null) {
    showError("Choose a valid expiration date.", "Invitation codes");
    return;
  }

  const updated = await invitationCodesStore.updateInvitationCode(invitationCodeId, {
    expires_at: expiresAt,
  });
  syncInvitationCodeInputs();

  if (updated) {
    showSuccess("Invitation code updated.", "Invitation codes");
  }
}

async function deleteInvitationCodeEntry(invitationCodeId: string): Promise<void> {
  const deleted = await invitationCodesStore.deleteInvitationCode(invitationCodeId);
  syncInvitationCodeInputs();

  if (deleted) {
    showSuccess("Invitation code deleted.", "Invitation codes");
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
          Timestamps render in your browser timezone. This profile timezone controls how the
          app should interpret day boundaries for tracking logic.
        </p>

        <label class="field">
          <span class="label">Avatar image</span>
          <input class="native-file-input" type="file" accept="image/*" @change="uploadAvatar" />
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
    :visible="invitationCodesVisible"
    modal
    header="Invitation codes"
    class="profile-dialog"
    :style="{ width: 'min(56rem, 96vw)' }"
    @update:visible="(value) => emit('update:invitationCodesVisible', value)"
  >
    <div class="dialog-stack">
      <div v-if="invitationCodesStore.viewState === 'loading'" class="loading shell-center">
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
              New accounts can sign up with any active code until it expires or you delete it.
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
            <p>Review expiration, delete old codes, and see which accounts came from each one.</p>
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
              <span>Created {{ formatDateTime(invitationCode.created_at) }}</span>
              <span>Expires {{ formatDateTime(invitationCode.expires_at) }}</span>
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
                  :loading="invitationCodesStore.submissionState === 'submitting'"
                  @click="saveInvitationCode(invitationCode.id)"
                />
                <Button
                  label="Delete"
                  icon="pi pi-trash"
                  severity="danger"
                  :loading="invitationCodesStore.submissionState === 'submitting'"
                  @click="deleteInvitationCodeEntry(invitationCode.id)"
                />
              </div>
            </div>

            <div class="invitation-code-users">
              <p class="label">Users created with this code</p>
              <div v-if="invitationCode.users_created.length === 0" class="invitation-code-empty">
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
.dialog-stack,
.dialog-section,
.field,
.invitation-code-actions,
.invitation-code-users,
.invitation-code-user-list {
  display: grid;
  gap: 0.75rem;
}

.profile-dialog :deep(.p-dialog-content) {
  padding-top: 0.25rem;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.section-heading-text h3,
.section-heading h3 {
  margin: 0;
  font-size: 1.1rem;
}

.section-heading-text p,
.section-heading p {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  color: #334155;
}

.dialog-copy {
  margin: 0;
  line-height: 1.7;
  color: #334155;
}

.danger-section {
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(185, 28, 28, 0.04);
}

.loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.shell-center {
  justify-content: center;
  min-height: 12rem;
}

.empty-invitation-state {
  color: #64748b;
}

.invitation-code-card {
  display: grid;
  gap: 1rem;
  padding: 1.1rem;
  border-radius: 1rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.8);
}

.invitation-code-header,
.invitation-code-meta,
.invitation-code-buttons,
.invitation-code-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.invitation-code-header {
  align-items: flex-start;
}

.invitation-code-copy {
  display: grid;
  gap: 0.35rem;
}

.code-label {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.invitation-code-copy code {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.95rem;
  word-break: break-all;
  color: #0f172a;
}

.invitation-code-meta {
  flex-wrap: wrap;
  justify-content: flex-start;
  color: #475569;
  font-size: 0.92rem;
}

.invitation-code-empty {
  color: #64748b;
}

.invitation-code-user-list {
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
}

.invitation-code-user {
  justify-content: flex-start;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border-radius: 0.9rem;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
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
  .invitation-code-header,
  .invitation-code-buttons,
  .invitation-code-user {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
