<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Card from "primevue/card";
import Dialog from "primevue/dialog";
import Divider from "primevue/divider";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import Message from "primevue/message";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";
import Tag from "primevue/tag";

import { useAuthStore } from "../stores/auth";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const statusStore = useStatusStore();

const username = ref("");
const password = ref("");

const activeTabIndex = ref(0);
const profileDialogVisible = ref(false);
const passwordDialogVisible = ref(false);
const deleteAccountDialogVisible = ref(false);
const profileMenu = ref<InstanceType<typeof Menu> | null>(null);

const displayNameInput = ref("");
const currentPasswordInput = ref("");
const newPasswordInput = ref("");
const deletePasswordInput = ref("");
const profileSuccessMessage = ref("");
const profileErrorMessage = ref("");
const passwordSuccessMessage = ref("");
const passwordErrorMessage = ref("");
const deleteAccountErrorMessage = ref("");

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

  return "Sign in";
});

const authSummary = computed(() => {
  if (authStore.bootstrapRequired) {
    return "The first account becomes the administrator and unlocks the rest of the app.";
  }

  return "Use the session-backed login flow to move into the Phase 1 app shell.";
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

const profileMenuItems = computed<MenuItem[]>(() => [
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
]);

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

function toggleProfileMenu(event: Event): void {
  profileMenu.value?.toggle(event);
}

async function submitAuthForm(): Promise<void> {
  const credentials = {
    password: password.value,
    username: username.value,
  };

  if (authStore.bootstrapRequired) {
    await authStore.bootstrap(credentials);
  } else {
    await authStore.login(credentials);
  }
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

watch(
  () => authStore.currentUser,
  () => {
    syncProfileInputs();
    resetPasswordInputs();
    resetDeleteAccountInputs();
  },
  { immediate: true },
);

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
        <TabView v-model:activeIndex="activeTabIndex">
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
    </section>

    <section v-else class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Phase 1 Started</p>
        <h1>Goal tracking with a real account flow.</h1>
        <p class="summary">
          The app can now bootstrap its first administrator account, restore sessions, and sign in
          through the same API stack the rest of Phase 1 will build on.
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

          <form v-else class="auth-form" @submit.prevent="submitAuthForm">
            <Message v-if="authStore.errorMessage !== ''" severity="error" :closable="false">
              {{ authStore.errorMessage }}
            </Message>

            <label class="field">
              <span class="label">Username</span>
              <InputText v-model="username" autocomplete="username" />
            </label>

            <label class="field">
              <span class="label">Password</span>
              <Password
                v-model="password"
                input-class="full-width-input"
                autocomplete="current-password"
                :feedback="false"
                toggle-mask
              />
            </label>

            <Button
              type="submit"
              :label="authStore.bootstrapRequired ? 'Create admin account' : 'Sign in'"
              icon="pi pi-arrow-right"
              :loading="isBusy"
            />
          </form>
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

.native-file-input {
  padding: 0.8rem 0.9rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.85rem;
  background: #fff;
}

.auth-card :deep(.full-width-input),
.profile-dialog :deep(.full-width-input) {
  width: 100%;
}

.auth-card :deep(.p-password),
.profile-dialog :deep(.p-password) {
  width: 100%;
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

  .profile-name {
    max-width: 10rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
