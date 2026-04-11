<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import { useAuthStore } from "../stores/auth";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const statusStore = useStatusStore();
const username = ref("");
const password = ref("");

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

onMounted(() => {
  void statusStore.loadStatus();
  void authStore.initialize();
});
</script>

<template>
  <main class="home-view">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Phase 1 Started</p>
        <h1>Goal tracking with a real account flow.</h1>
        <p class="summary" v-if="authStore.isAuthenticated">
          The backend session foundation from Phase 0 is now driving a real signed-in app shell.
          This is the base for metrics, goals, entries, and dashboards.
        </p>
        <p class="summary" v-else>
          The app can now bootstrap its first administrator account, restore sessions, and sign in
          through the same API stack the rest of Phase 1 will build on.
        </p>
        <div class="actions" v-if="authStore.isAuthenticated">
          <Button
            label="Sign out"
            icon="pi pi-sign-out"
            severity="secondary"
            :loading="authStore.submissionState === 'submitting'"
            @click="authStore.logout"
          />
          <Button label="Refresh status" icon="pi pi-refresh" @click="statusStore.loadStatus" />
        </div>
      </div>
      <Card class="status-card auth-card">
        <template #title>
          {{ authStore.isAuthenticated ? "Signed-in shell" : authTitle }}
        </template>
        <template #subtitle>
          {{ authStore.isAuthenticated ? "Session-backed Phase 1 entry point" : authSummary }}
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

          <div v-else-if="authStore.isAuthenticated" class="status-stack">
            <div class="status-row">
              <span class="label">User</span>
              <strong>{{ authStore.currentUser?.username }}</strong>
            </div>

            <div class="status-row">
              <span class="label">Role</span>
              <Tag
                :value="authStore.currentUser?.is_admin ? 'administrator' : 'user'"
                :severity="authStore.currentUser?.is_admin ? 'success' : 'info'"
              />
            </div>

            <div class="phase-grid">
              <div class="phase-item">
                <p class="phase-label">Profile basics</p>
                <strong>Active</strong>
                <span>Session state and signed-in identity are now visible in the app.</span>
              </div>
              <div class="phase-item">
                <p class="phase-label">Next up</p>
                <strong>Metrics and goals</strong>
                <span>Phase 1 now has a stable authenticated shell to build on.</span>
              </div>
            </div>
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

            <div v-if="statusStore.state === 'loading'" class="loading">
              <ProgressSpinner
                strokeWidth="5"
                style="width: 2.5rem; height: 2.5rem"
                animationDuration=".8s"
              />
              <span>Requesting status from the API.</span>
            </div>

            <p v-if="statusStore.state === 'error'" class="error">
              {{ statusStore.errorMessage }}
            </p>
          </div>
        </template>
      </Card>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: 3rem 1.5rem;
}

.hero {
  display: grid;
  gap: 1.5rem;
  align-items: start;
  max-width: 1100px;
  margin: 0 auto;
}

.hero-copy {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 1.5rem;
  padding: 2rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.eyebrow {
  margin: 0 0 1rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 0.95;
}

.summary {
  max-width: 48rem;
  margin: 1.25rem 0 0;
  font-size: 1.1rem;
  line-height: 1.7;
  color: #334155;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.status-card {
  border-radius: 1.5rem;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.status-stack {
  display: grid;
  gap: 1rem;
}

.auth-form {
  display: grid;
  gap: 1rem;
}

.field {
  display: grid;
  gap: 0.45rem;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.label {
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
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

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 600;
}

.auth-card :deep(.full-width-input) {
  width: 100%;
}

.auth-card :deep(.p-password) {
  width: 100%;
}

.phase-grid {
  display: grid;
  gap: 1rem;
}

.phase-item {
  display: grid;
  gap: 0.35rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.04);
}

.phase-label {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}

code {
  padding: 0.1rem 0.35rem;
  border-radius: 0.35rem;
  background: rgba(148, 163, 184, 0.16);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.15fr 1fr 0.95fr;
  }
}
</style>
