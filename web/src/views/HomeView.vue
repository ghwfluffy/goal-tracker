<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import Message from "primevue/message";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";
import Tag from "primevue/tag";

import { useAuthStore } from "../stores/auth";
import { useInvitationCodesStore } from "../stores/invitationCodes";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const invitationCodesStore = useInvitationCodesStore();
const statusStore = useStatusStore();

const loginUsername = ref("");
const loginPassword = ref("");
const signupUsername = ref("");
const signupPassword = ref("");
const signupInvitationCode = ref("");
const signupExampleData = ref(false);

const dashboardTabIndex = ref(0);
const authTabIndex = ref(0);
const profileDialogVisible = ref(false);
const passwordDialogVisible = ref(false);
const deleteAccountDialogVisible = ref(false);
const invitationCodesDialogVisible = ref(false);
const profileMenu = ref<InstanceType<typeof Menu> | null>(null);

const displayNameInput = ref("");
const currentPasswordInput = ref("");
const newPasswordInput = ref("");
const deletePasswordInput = ref("");
const createInvitationCodeExpiresAt = ref("");
const invitationCodeExpiresAtInputs = ref<Record<string, string>>({});
const profileSuccessMessage = ref("");
const profileErrorMessage = ref("");
const passwordSuccessMessage = ref("");
const passwordErrorMessage = ref("");
const deleteAccountErrorMessage = ref("");
const invitationCodesSuccessMessage = ref("");

const lastCheckedLabel = computed(() => {
  if (statusStore.data === null) {
    return "Waiting for the first successful API call.";
  }

  return new Date(statusStore.data.checked_at).toLocaleString();
});

const authTitle = computed(() => {
  if (authStore.bootstrapRequired) {
    return "Create the first account";
  }

  return "Access your account";
});

const authSummary = computed(() => {
  if (authStore.bootstrapRequired) {
    return "The first account becomes the administrator and unlocks invited signups.";
  }

  return "Sign in with an existing account or use an invitation code to register.";
});

const isBusy = computed(() => {
  return authStore.viewState === "loading" || authStore.submissionState === "submitting";
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

const profileMenuItems = computed<MenuItem[]>(() => {
  const items: MenuItem[] = [
    {
      icon: "pi pi-user-edit",
      label: "Edit profile",
      command: () => {
        openProfileDialog();
      },
    },
    {
      icon: "pi pi-key",
      label: "Change password",
      command: () => {
        openPasswordDialog();
      },
    },
  ];

  if (authStore.currentUser?.is_admin) {
    items.push({
      icon: "pi pi-ticket",
      label: "Invitation codes",
      command: () => {
        void openInvitationCodesDialog();
      },
    });
  }

  items.push(
    {
      icon: "pi pi-trash",
      label: "Delete account",
      command: () => {
        openDeleteAccountDialog();
      },
    },
    {
      icon: "pi pi-sign-out",
      label: "Sign out",
      command: () => {
        void authStore.logout();
      },
    },
  );

  return items;
});

function resetProfileMessages(): void {
  profileSuccessMessage.value = "";
  profileErrorMessage.value = "";
}

function resetPasswordMessages(): void {
  passwordSuccessMessage.value = "";
  passwordErrorMessage.value = "";
}

function resetDeleteAccountMessages(): void {
  deleteAccountErrorMessage.value = "";
}

function resetInvitationCodeMessages(): void {
  invitationCodesSuccessMessage.value = "";
  invitationCodesStore.errorMessage = "";
}

function syncProfileInputs(): void {
  displayNameInput.value = authStore.currentUser?.display_name ?? "";
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

function openProfileDialog(): void {
  resetProfileMessages();
  syncProfileInputs();
  profileDialogVisible.value = true;
}

function openPasswordDialog(): void {
  resetPasswordMessages();
  resetPasswordInputs();
  passwordDialogVisible.value = true;
}

function openDeleteAccountDialog(): void {
  resetDeleteAccountMessages();
  resetDeleteAccountInputs();
  deleteAccountDialogVisible.value = true;
}

async function openInvitationCodesDialog(): Promise<void> {
  resetInvitationCodeMessages();
  createInvitationCodeExpiresAt.value = defaultInvitationCodeExpiration();
  invitationCodesDialogVisible.value = true;
  await invitationCodesStore.loadInvitationCodes();
  syncInvitationCodeInputs();
}

function toggleProfileMenu(event: Event): void {
  profileMenu.value?.toggle(event);
}

async function submitBootstrapForm(): Promise<void> {
  await authStore.bootstrap({
    password: loginPassword.value,
    username: loginUsername.value,
  });
}

async function submitLoginForm(): Promise<void> {
  await authStore.login({
    password: loginPassword.value,
    username: loginUsername.value,
  });
}

async function submitSignupForm(): Promise<void> {
  await authStore.register({
    invitation_code: signupInvitationCode.value,
    is_example_data: signupExampleData.value,
    password: signupPassword.value,
    username: signupUsername.value,
  });
}

async function saveProfile(): Promise<void> {
  resetProfileMessages();

  const updated = await authStore.updateProfile({
    display_name: displayNameInput.value.trim() === "" ? null : displayNameInput.value,
  });

  if (updated) {
    profileSuccessMessage.value = "Profile updated.";
  } else {
    profileErrorMessage.value = authStore.errorMessage;
  }
}

async function changePassword(): Promise<void> {
  resetPasswordMessages();

  const updated = await authStore.changePassword({
    current_password: currentPasswordInput.value,
    new_password: newPasswordInput.value,
  });

  if (updated) {
    passwordSuccessMessage.value = "Password changed.";
    resetPasswordInputs();
  } else {
    passwordErrorMessage.value = authStore.errorMessage;
  }
}

async function uploadAvatar(event: Event): Promise<void> {
  resetProfileMessages();

  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file === undefined) {
    return;
  }

  const uploaded = await authStore.uploadAvatar(file);
  if (uploaded) {
    profileSuccessMessage.value = "Avatar updated.";
  } else {
    profileErrorMessage.value = authStore.errorMessage;
  }

  input.value = "";
}

async function deleteAccount(): Promise<void> {
  resetDeleteAccountMessages();

  const deleted = await authStore.deleteAccount({
    password: deletePasswordInput.value,
  });

  if (deleted) {
    deleteAccountDialogVisible.value = false;
    return;
  }

  deleteAccountErrorMessage.value = authStore.errorMessage;
}

async function createNewInvitationCode(): Promise<void> {
  resetInvitationCodeMessages();
  const expiresAt = toIsoDateTime(createInvitationCodeExpiresAt.value);
  if (expiresAt === null) {
    invitationCodesStore.errorMessage = "Choose a valid expiration date.";
    return;
  }

  const created = await invitationCodesStore.createInvitationCode({ expires_at: expiresAt });
  syncInvitationCodeInputs();

  if (created) {
    invitationCodesSuccessMessage.value = "Invitation code created.";
    createInvitationCodeExpiresAt.value = defaultInvitationCodeExpiration();
  }
}

async function saveInvitationCode(invitationCodeId: string): Promise<void> {
  resetInvitationCodeMessages();
  const expiresAt = toIsoDateTime(invitationCodeExpiresAtInputs.value[invitationCodeId] ?? "");
  if (expiresAt === null) {
    invitationCodesStore.errorMessage = "Choose a valid expiration date.";
    return;
  }

  const updated = await invitationCodesStore.updateInvitationCode(invitationCodeId, {
    expires_at: expiresAt,
  });
  syncInvitationCodeInputs();

  if (updated) {
    invitationCodesSuccessMessage.value = "Invitation code updated.";
  }
}

async function deleteInvitationCodeEntry(invitationCodeId: string): Promise<void> {
  resetInvitationCodeMessages();
  const deleted = await invitationCodesStore.deleteInvitationCode(invitationCodeId);
  syncInvitationCodeInputs();

  if (deleted) {
    invitationCodesSuccessMessage.value = "Invitation code deleted.";
  }
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
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

watch(authTabIndex, () => {
  authStore.errorMessage = "";
});

onMounted(() => {
  void statusStore.loadStatus();
  void authStore.initialize();
});
</script>

<template>
  <main class="home-view">
    <section v-if="authStore.isAuthenticated" class="app-shell">
      <header class="app-header">
        <div class="brand-block">
          <p class="eyebrow">Phase 1</p>
          <h1 class="brand-title">Goal Tracker</h1>
          <p class="brand-summary">Track goals, dashboards, and updates from one responsive app.</p>
        </div>

        <div class="header-actions">
          <Tag
            v-if="statusStore.state === 'ready' && statusStore.data !== null"
            :value="`v${statusStore.data.version}`"
            severity="success"
          />
          <Button
            class="profile-button"
            severity="secondary"
            text
            @click="toggleProfileMenu"
          >
            <span class="profile-button-content">
              <Avatar
                :image="avatarUrl ?? undefined"
                :label="avatarUrl === null ? avatarLabel : undefined"
                shape="circle"
              />
              <span class="profile-name">{{ currentDisplayName }}</span>
            </span>
          </Button>
          <Menu ref="profileMenu" :model="profileMenuItems" popup />
        </div>
      </header>

      <section class="tabs-shell">
        <TabView v-model:activeIndex="dashboardTabIndex">
          <TabPanel header="Dashboards">
            <div class="panel-card blank-panel">
              <p class="panel-eyebrow">Dashboards</p>
              <h2>Blank for now</h2>
              <p>
                This tab is intentionally empty for this slice. The shell and navigation are in
                place so saved dashboard widgets can be added next.
              </p>
            </div>
          </TabPanel>
          <TabPanel header="Goals">
            <div class="goals-grid">
              <div class="panel-card">
                <p class="panel-eyebrow">Goals</p>
                <h2>Core tracking is next</h2>
                <p>
                  Goal CRUD, metric history, entries, and per-goal status views will land on top
                  of this signed-in shell.
                </p>
              </div>

              <div class="panel-card">
                <p class="panel-eyebrow">Application Status</p>
                <h2>Smoke test still live</h2>
                <div class="status-stack">
                  <div class="status-row">
                    <span class="label">State</span>
                    <Tag
                      v-if="statusStore.state === 'ready' && statusStore.data !== null"
                      :value="statusStore.data.status"
                      severity="success"
                    />
                    <Tag v-else-if="statusStore.state === 'error'" value="error" severity="danger" />
                    <Tag v-else value="loading" severity="warning" />
                  </div>

                  <div class="status-row">
                    <span class="label">Version</span>
                    <strong>{{ statusStore.data?.version ?? "pending" }}</strong>
                  </div>

                  <div class="status-row">
                    <span class="label">Checked</span>
                    <span>{{ lastCheckedLabel }}</span>
                  </div>

                  <div v-if="statusStore.state === 'loading'" class="loading">
                    <ProgressSpinner
                      strokeWidth="5"
                      style="width: 2rem; height: 2rem"
                      animationDuration=".8s"
                    />
                    <span>Refreshing API status.</span>
                  </div>

                  <Message
                    v-if="statusStore.state === 'error'"
                    severity="error"
                    :closable="false"
                  >
                    {{ statusStore.errorMessage }}
                  </Message>
                </div>
              </div>
            </div>
          </TabPanel>
        </TabView>
      </section>

      <Dialog
        v-model:visible="profileDialogVisible"
        modal
        header="Edit profile"
        class="profile-dialog"
        :style="{ width: 'min(44rem, 96vw)' }"
      >
        <div class="dialog-stack">
          <Message v-if="profileSuccessMessage !== ''" severity="success" :closable="false">
            {{ profileSuccessMessage }}
          </Message>
          <Message v-if="profileErrorMessage !== ''" severity="error" :closable="false">
            {{ profileErrorMessage }}
          </Message>

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
        v-model:visible="passwordDialogVisible"
        modal
        header="Change password"
        class="profile-dialog"
        :style="{ width: 'min(32rem, 96vw)' }"
      >
        <div class="dialog-stack">
          <Message v-if="passwordSuccessMessage !== ''" severity="success" :closable="false">
            {{ passwordSuccessMessage }}
          </Message>
          <Message v-if="passwordErrorMessage !== ''" severity="error" :closable="false">
            {{ passwordErrorMessage }}
          </Message>

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
        v-model:visible="deleteAccountDialogVisible"
        modal
        header="Delete account"
        class="profile-dialog"
        :style="{ width: 'min(32rem, 96vw)' }"
      >
        <div class="dialog-stack">
          <Message v-if="deleteAccountErrorMessage !== ''" severity="error" :closable="false">
            {{ deleteAccountErrorMessage }}
          </Message>

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
        v-model:visible="invitationCodesDialogVisible"
        modal
        header="Invitation codes"
        class="profile-dialog"
        :style="{ width: 'min(56rem, 96vw)' }"
      >
        <div class="dialog-stack">
          <Message
            v-if="invitationCodesSuccessMessage !== ''"
            severity="success"
            :closable="false"
          >
            {{ invitationCodesSuccessMessage }}
          </Message>
          <Message
            v-if="invitationCodesStore.errorMessage !== ''"
            severity="error"
            :closable="false"
          >
            {{ invitationCodesStore.errorMessage }}
          </Message>

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
                <p>Review expiration, revoke old codes, and see which accounts came from each one.</p>
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
                  <Tag
                    :value="invitationCode.revoked_at === null ? 'active' : 'deleted'"
                    :severity="invitationCode.revoked_at === null ? 'success' : 'danger'"
                  />
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
                      :disabled="invitationCode.revoked_at !== null"
                    />
                  </label>

                  <div class="invitation-code-buttons">
                    <Button
                      label="Save"
                      icon="pi pi-save"
                      severity="secondary"
                      :disabled="invitationCode.revoked_at !== null"
                      :loading="invitationCodesStore.submissionState === 'submitting'"
                      @click="saveInvitationCode(invitationCode.id)"
                    />
                    <Button
                      label="Delete"
                      icon="pi pi-trash"
                      severity="danger"
                      :disabled="invitationCode.revoked_at !== null"
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
    </section>

    <section v-else class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Phase 1 Started</p>
        <h1>Goal tracking with a real account flow.</h1>
        <p class="summary">
          The app can now bootstrap its first administrator, manage invitation-based signup, restore
          sessions, and distinguish example-data accounts for feature testing.
        </p>
      </div>

      <Card class="status-card auth-card">
        <template #title>
          {{ authTitle }}
        </template>
        <template #subtitle>
          {{ authSummary }}
        </template>
        <template #content>
          <div v-if="authStore.viewState === 'loading'" class="loading shell-center">
            <ProgressSpinner
              strokeWidth="5"
              style="width: 2.5rem; height: 2.5rem"
              animationDuration=".8s"
            />
            <span>Restoring session state.</span>
          </div>

          <div v-else class="auth-form">
            <Message v-if="authStore.errorMessage !== ''" severity="error" :closable="false">
              {{ authStore.errorMessage }}
            </Message>

            <form
              v-if="authStore.bootstrapRequired"
              class="auth-form"
              @submit.prevent="submitBootstrapForm"
            >
              <label class="field">
                <span class="label">Username</span>
                <InputText v-model="loginUsername" autocomplete="username" />
              </label>

              <label class="field">
                <span class="label">Password</span>
                <Password
                  v-model="loginPassword"
                  input-class="full-width-input"
                  autocomplete="new-password"
                  :feedback="false"
                  toggle-mask
                />
              </label>

              <Button
                type="submit"
                label="Create admin account"
                icon="pi pi-arrow-right"
                :loading="isBusy"
              />
            </form>

            <TabView v-else v-model:activeIndex="authTabIndex">
              <TabPanel header="Sign in">
                <form class="auth-form" @submit.prevent="submitLoginForm">
                  <label class="field">
                    <span class="label">Username</span>
                    <InputText v-model="loginUsername" autocomplete="username" />
                  </label>

                  <label class="field">
                    <span class="label">Password</span>
                    <Password
                      v-model="loginPassword"
                      input-class="full-width-input"
                      autocomplete="current-password"
                      :feedback="false"
                      toggle-mask
                    />
                  </label>

                  <Button
                    type="submit"
                    label="Sign in"
                    icon="pi pi-arrow-right"
                    :loading="isBusy"
                  />
                </form>
              </TabPanel>

              <TabPanel header="Sign up">
                <form class="auth-form" @submit.prevent="submitSignupForm">
                  <label class="field">
                    <span class="label">Username</span>
                    <InputText v-model="signupUsername" autocomplete="username" />
                  </label>

                  <label class="field">
                    <span class="label">Password</span>
                    <Password
                      v-model="signupPassword"
                      input-class="full-width-input"
                      autocomplete="new-password"
                      :feedback="false"
                      toggle-mask
                    />
                  </label>

                  <label class="field">
                    <span class="label">Registration code</span>
                    <InputText
                      v-model="signupInvitationCode"
                      autocomplete="one-time-code"
                    />
                  </label>

                  <label class="checkbox-row">
                    <Checkbox v-model="signupExampleData" binary input-id="signup-example-data" />
                    <span>Add example data</span>
                  </label>

                  <Button
                    type="submit"
                    label="Create account"
                    icon="pi pi-user-plus"
                    :loading="isBusy"
                  />
                </form>
              </TabPanel>
            </TabView>
          </div>
        </template>
      </Card>

      <Card class="status-card">
        <template #title>Application status</template>
        <template #subtitle>Backend connectivity and version smoke test</template>
        <template #content>
          <div class="status-stack">
            <div class="status-row">
              <span class="label">State</span>
              <Tag
                v-if="statusStore.state === 'ready' && statusStore.data !== null"
                :value="statusStore.data.status"
                severity="success"
              />
              <Tag v-else-if="statusStore.state === 'error'" value="error" severity="danger" />
              <Tag v-else value="loading" severity="warning" />
            </div>

            <div class="status-row">
              <span class="label">Version</span>
              <strong>{{ statusStore.data?.version ?? "pending" }}</strong>
            </div>

            <div class="status-row">
              <span class="label">Environment</span>
              <span>{{ statusStore.data?.environment ?? "unknown" }}</span>
            </div>

            <div class="status-row">
              <span class="label">Checked</span>
              <span>{{ lastCheckedLabel }}</span>
            </div>
          </div>
        </template>
      </Card>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: 1.5rem;
}

.app-shell,
.hero {
  max-width: 1180px;
  margin: 0 auto;
}

.app-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1.5rem 1.75rem;
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(31, 41, 55, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.hero {
  display: grid;
  gap: 1.5rem;
  align-items: start;
}

.hero-copy {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 1.5rem;
  padding: 2rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.eyebrow,
.panel-eyebrow {
  margin: 0 0 0.9rem;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

.brand-title,
h1,
h2,
h3 {
  margin: 0;
}

.brand-title {
  font-size: clamp(1.9rem, 4vw, 2.8rem);
}

h1 {
  max-width: 12ch;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 0.95;
}

.brand-summary,
.summary,
.panel-card p,
.section-heading-text p,
.section-heading p {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  color: #334155;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-button :deep(.p-button-label) {
  flex: 0 0 auto;
}

.profile-button-content {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-name {
  font-weight: 600;
  color: #0f172a;
}

.tabs-shell {
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(31, 41, 55, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.goals-grid {
  display: grid;
  gap: 1rem;
}

.panel-card,
.status-card {
  border-radius: 1.35rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.84);
  padding: 1.4rem;
}

.blank-panel {
  min-height: 16rem;
}

.status-stack,
.auth-form,
.dialog-stack,
.dialog-section,
.field {
  display: grid;
  gap: 1rem;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.label {
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
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
  font-size: 1.1rem;
}

.danger-section {
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(185, 28, 28, 0.04);
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  color: #0f172a;
}

.native-file-input {
  padding: 0.8rem 0.9rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.85rem;
  background: #fff;
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

.invitation-code-actions,
.invitation-code-users,
.invitation-code-user-list {
  display: grid;
  gap: 0.75rem;
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

.auth-card :deep(.full-width-input),
.profile-dialog :deep(.full-width-input) {
  width: 100%;
}

.auth-card :deep(.p-password),
.profile-dialog :deep(.p-password) {
  width: 100%;
}

.auth-card :deep(.p-tabview-panels) {
  padding-inline: 0;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.15fr 1fr 0.95fr;
  }

  .goals-grid {
    grid-template-columns: 1.1fr 0.9fr;
  }
}

@media (max-width: 720px) {
  .home-view {
    padding: 1rem;
  }

  .app-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: space-between;
  }

  .invitation-code-header,
  .invitation-code-buttons,
  .invitation-code-user {
    align-items: flex-start;
    flex-direction: column;
  }

  .profile-name {
    max-width: 10rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
