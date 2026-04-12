<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Card from "primevue/card";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";
import Tag from "primevue/tag";

import { useAuthStore } from "../../stores/auth";
import { useStatusStore } from "../../stores/status";

const authStore = useAuthStore();
const statusStore = useStatusStore();

const loginUsername = ref("");
const loginPassword = ref("");
const signupUsername = ref("");
const signupPassword = ref("");
const signupInvitationCode = ref("");
const signupExampleData = ref(false);
const authTabIndex = ref(0);

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

const lastCheckedLabel = computed(() => {
  if (statusStore.data === null) {
    return "Waiting for the first successful API call.";
  }

  return new Date(statusStore.data.checked_at).toLocaleString();
});

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

watch(authTabIndex, () => {
  authStore.errorMessage = "";
});
</script>

<template>
  <section class="hero">
    <div class="hero-copy surface-panel-soft">
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
</template>

<style scoped>
.hero {
  display: grid;
  gap: var(--space-9);
  align-items: start;
}

.hero-copy {
  padding: var(--space-11);
}

h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 0.95;
}

.summary {
  margin: var(--space-4) 0 0;
  line-height: var(--line-height-copy);
  color: var(--color-text-muted);
}

.status-stack,
.auth-form {
  display: grid;
  gap: var(--space-6);
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
}

.loading {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--color-text-strong);
}

.auth-card :deep(.full-width-input) {
  width: 100%;
}

.auth-card :deep(.p-password) {
  width: 100%;
}

.auth-card :deep(.p-tabview-panels) {
  padding-inline: 0;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.15fr 1fr 0.95fr;
  }
}
</style>
