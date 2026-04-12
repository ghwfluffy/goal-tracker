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

import { joinBasePath } from "../../lib/basePath";
import { useAuthStore } from "../../stores/auth";

const authStore = useAuthStore();
const guestLogoUrl = joinBasePath(import.meta.env.BASE_URL, "/logo-large.png");

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
  <section class="guest-auth-shell">
    <img class="guest-logo" :src="guestLogoUrl" alt="Goal Tracker" />

    <Card class="auth-card">
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
  </section>
</template>

<style scoped>
.guest-auth-shell {
  min-height: 100vh;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: var(--space-8);
  padding: var(--space-9);
}

.guest-logo {
  width: min(100%, 34rem);
  height: auto;
  display: block;
}

.auth-form {
  display: grid;
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

.auth-card {
  width: min(100%, 34rem);
}

.auth-card :deep(.p-tabview-panels) {
  padding-inline: 0;
}

@media (min-width: 900px) {
  .guest-auth-shell {
    grid-template-columns: minmax(18rem, 30rem) minmax(20rem, 34rem);
    align-items: center;
    justify-content: center;
    justify-items: stretch;
    column-gap: clamp(4rem, 8vw, 7rem);
  }

  .guest-logo {
    width: min(100%, 28rem);
    justify-self: end;
    margin-inline-end: clamp(1rem, 2.5vw, 2.5rem);
  }

  .auth-card {
    justify-self: start;
  }
}
</style>
