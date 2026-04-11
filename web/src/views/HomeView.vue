<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Card from "primevue/card";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import Dropdown from "primevue/dropdown";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import Message from "primevue/message";
import Password from "primevue/password";
import ProgressSpinner from "primevue/progressspinner";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";
import Tag from "primevue/tag";

import DashboardWorkspace from "../components/DashboardWorkspace.vue";
import { DEFAULT_PROFILE_TIMEZONE, formatDateOnly, formatTimestampInBrowserTimezone } from "../lib/time";
import { useAuthStore } from "../stores/auth";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";
import { useInvitationCodesStore } from "../stores/invitationCodes";
import { useMetricsStore } from "../stores/metrics";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const dashboardsStore = useDashboardsStore();
const goalsStore = useGoalsStore();
const invitationCodesStore = useInvitationCodesStore();
const metricsStore = useMetricsStore();
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
const timezoneInput = ref(DEFAULT_PROFILE_TIMEZONE);
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
const metricSuccessMessage = ref("");
const goalSuccessMessage = ref("");

const metricNameInput = ref("");
const metricTypeInput = ref<"number" | "date">("number");
const metricDecimalPlacesInput = ref("0");
const metricUnitLabelInput = ref("");
const metricInitialNumberValueInput = ref("");
const metricInitialDateValueInput = ref("");
const metricEntryNumberInputs = ref<Record<string, string>>({});
const metricEntryDateInputs = ref<Record<string, string>>({});

const goalTitleInput = ref("");
const goalDescriptionInput = ref("");
const goalStartDateInput = ref(new Date().toISOString().slice(0, 10));
const goalTargetDateInput = ref("");
const goalTargetNumberValueInput = ref("");
const goalTargetDateValueInput = ref("");
const goalUseNewMetric = ref(false);
const goalMetricIdInput = ref("");
const goalNewMetricNameInput = ref("");
const goalNewMetricTypeInput = ref<"number" | "date">("number");
const goalNewMetricDecimalPlacesInput = ref("0");
const goalNewMetricUnitLabelInput = ref("");
const goalNewMetricInitialNumberValueInput = ref("");
const goalNewMetricInitialDateValueInput = ref("");

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

const selectedGoalMetric = computed(() => {
  return activeMetrics.value.find((metric) => metric.id === goalMetricIdInput.value) ?? null;
});

const activeMetrics = computed(() => {
  return metricsStore.metrics.filter((metric) => !metric.is_archived);
});

const goalMetricType = computed(() => {
  if (goalUseNewMetric.value) {
    return goalNewMetricTypeInput.value;
  }

  return selectedGoalMetric.value?.metric_type ?? "number";
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

function resetMetricMessages(): void {
  metricSuccessMessage.value = "";
  metricsStore.errorMessage = "";
}

function resetGoalMessages(): void {
  goalSuccessMessage.value = "";
  goalsStore.errorMessage = "";
}

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

function resetMetricForm(): void {
  metricNameInput.value = "";
  metricTypeInput.value = "number";
  metricDecimalPlacesInput.value = "0";
  metricUnitLabelInput.value = "";
  metricInitialNumberValueInput.value = "";
  metricInitialDateValueInput.value = "";
}

function resetGoalForm(): void {
  goalTitleInput.value = "";
  goalDescriptionInput.value = "";
  goalStartDateInput.value = new Date().toISOString().slice(0, 10);
  goalTargetDateInput.value = "";
  goalTargetNumberValueInput.value = "";
  goalTargetDateValueInput.value = "";
  goalUseNewMetric.value = false;
  goalMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
  goalNewMetricNameInput.value = "";
  goalNewMetricTypeInput.value = "number";
  goalNewMetricDecimalPlacesInput.value = "0";
  goalNewMetricUnitLabelInput.value = "";
  goalNewMetricInitialNumberValueInput.value = "";
  goalNewMetricInitialDateValueInput.value = "";
}

function parseOptionalNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }

  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseDecimalPlaces(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : Math.trunc(value);
  }

  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function numberInputStep(decimalPlaces: number | null): string {
  const places = Math.max(decimalPlaces ?? 0, 0);
  if (places === 0) {
    return "1";
  }
  return `0.${"0".repeat(places - 1)}1`;
}

function formatNumberValue(value: number | null, decimalPlaces: number | null): string {
  if (value === null) {
    return "No value yet";
  }

  return value.toFixed(decimalPlaces ?? 0);
}

function formatMetricValue(
  metricType: "number" | "date",
  numberValue: number | null,
  dateValue: string | null,
  decimalPlaces: number | null,
): string {
  if (metricType === "number") {
    return formatNumberValue(numberValue, decimalPlaces);
  }

  return formatDateOnly(dateValue);
}

function syncMetricEntryInputs(): void {
  metricEntryNumberInputs.value = Object.fromEntries(metricsStore.metrics.map((metric) => [metric.id, ""]));
  metricEntryDateInputs.value = Object.fromEntries(metricsStore.metrics.map((metric) => [metric.id, ""]));
}

async function loadTrackingData(): Promise<void> {
  await Promise.all([
    dashboardsStore.loadDashboards(),
    metricsStore.loadMetrics(),
    goalsStore.loadGoals(),
  ]);
  if (goalMetricIdInput.value === "" && activeMetrics.value.length > 0) {
    goalMetricIdInput.value = activeMetrics.value[0].id;
  }
  syncMetricEntryInputs();
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
    timezone: timezoneInput.value.trim() === "" ? null : timezoneInput.value,
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

async function submitMetricForm(): Promise<void> {
  resetMetricMessages();
  const created = await metricsStore.createMetric({
    decimal_places: metricTypeInput.value === "number" ? parseDecimalPlaces(metricDecimalPlacesInput.value) : null,
    initial_date_value: metricTypeInput.value === "date" ? metricInitialDateValueInput.value || null : null,
    initial_number_value: metricTypeInput.value === "number" ? parseOptionalNumber(metricInitialNumberValueInput.value) : null,
    metric_type: metricTypeInput.value,
    name: metricNameInput.value,
    unit_label: metricUnitLabelInput.value.trim() === "" ? null : metricUnitLabelInput.value,
  });

  if (created) {
    metricSuccessMessage.value = "Metric created.";
    resetMetricForm();
    if (goalMetricIdInput.value === "" && activeMetrics.value.length > 0) {
      goalMetricIdInput.value = activeMetrics.value[0].id;
    }
    syncMetricEntryInputs();
  }
}

async function submitMetricEntry(metricId: string, metricType: "number" | "date"): Promise<void> {
  resetMetricMessages();
  const updated = await metricsStore.addMetricEntry(metricId, {
    date_value: metricType === "date" ? metricEntryDateInputs.value[metricId] || null : null,
    number_value: metricType === "number" ? parseOptionalNumber(metricEntryNumberInputs.value[metricId] ?? "") : null,
  });

  if (updated) {
    metricSuccessMessage.value = "Metric updated.";
    await goalsStore.loadGoals();
    syncMetricEntryInputs();
  }
}

async function submitGoalForm(): Promise<void> {
  resetGoalMessages();
  const created = await goalsStore.createGoal({
    description: goalDescriptionInput.value.trim() === "" ? null : goalDescriptionInput.value,
    metric_id: goalUseNewMetric.value ? null : goalMetricIdInput.value || null,
    new_metric: goalUseNewMetric.value
      ? {
          decimal_places:
            goalNewMetricTypeInput.value === "number"
              ? parseDecimalPlaces(goalNewMetricDecimalPlacesInput.value)
              : null,
          initial_date_value:
            goalNewMetricTypeInput.value === "date" ? goalNewMetricInitialDateValueInput.value || null : null,
          initial_number_value:
            goalNewMetricTypeInput.value === "number"
              ? parseOptionalNumber(goalNewMetricInitialNumberValueInput.value)
              : null,
          metric_type: goalNewMetricTypeInput.value,
          name: goalNewMetricNameInput.value,
          unit_label:
            goalNewMetricUnitLabelInput.value.trim() === "" ? null : goalNewMetricUnitLabelInput.value,
        }
      : null,
    start_date: goalStartDateInput.value,
    target_date: goalTargetDateInput.value || null,
    target_value_date: goalMetricType.value === "date" ? goalTargetDateValueInput.value || null : null,
    target_value_number:
      goalMetricType.value === "number" ? parseOptionalNumber(goalTargetNumberValueInput.value) : null,
    title: goalTitleInput.value,
  });

  if (created) {
    goalSuccessMessage.value = "Goal created.";
    resetGoalForm();
    await metricsStore.loadMetrics();
    syncMetricEntryInputs();
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

async function setMetricArchived(metricId: string, archived: boolean): Promise<void> {
  resetMetricMessages();
  const updated = await metricsStore.setMetricArchived(metricId, archived);
  if (updated) {
    metricSuccessMessage.value = archived ? "Metric archived." : "Metric restored.";
    await goalsStore.loadGoals();
    syncMetricEntryInputs();
    if (goalMetricIdInput.value !== "" && selectedGoalMetric.value === null) {
      goalMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }
  }
}

async function deleteMetricEntry(metricId: string): Promise<void> {
  resetMetricMessages();
  const deleted = await metricsStore.deleteMetric(metricId);
  if (deleted) {
    metricSuccessMessage.value = "Metric deleted.";
    await goalsStore.loadGoals();
    syncMetricEntryInputs();
    if (goalMetricIdInput.value !== "" && selectedGoalMetric.value === null) {
      goalMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }
  }
}

function formatDateTime(value: string): string {
  return formatTimestampInBrowserTimezone(value);
}

watch(
  () => authStore.currentUser,
  async () => {
    syncProfileInputs();
    resetPasswordInputs();
    resetDeleteAccountInputs();
    if (authStore.currentUser !== null) {
      await loadTrackingData();
      return;
    }

    metricsStore.reset();
    dashboardsStore.reset();
    goalsStore.reset();
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

watch(
  () => metricsStore.metrics,
  () => {
    if (!goalUseNewMetric.value && selectedGoalMetric.value === null) {
      goalMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }
  },
  { deep: true },
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
            <DashboardWorkspace />
          </TabPanel>
          <TabPanel header="Metrics">
            <div class="tracking-grid">
              <div class="panel-card">
                <p class="panel-eyebrow">Metrics</p>
                <h2>Create a reusable metric</h2>
                <p>
                  Metrics hold the values you update over time. Goals can reference them instead of
                  owning isolated history.
                </p>

                <div class="form-stack">
                  <Message v-if="metricSuccessMessage !== ''" severity="success" :closable="false">
                    {{ metricSuccessMessage }}
                  </Message>
                  <Message v-if="metricsStore.errorMessage !== ''" severity="error" :closable="false">
                    {{ metricsStore.errorMessage }}
                  </Message>

                  <label class="field">
                    <span class="label">Metric name</span>
                    <InputText v-model="metricNameInput" />
                  </label>

                  <label class="field">
                    <span class="label">Metric type</span>
                    <select v-model="metricTypeInput" class="native-file-input">
                      <option value="number">Number</option>
                      <option value="date">Date</option>
                    </select>
                  </label>

                  <label v-if="metricTypeInput === 'number'" class="field">
                    <span class="label">Decimal places</span>
                    <input
                      v-model="metricDecimalPlacesInput"
                      class="native-file-input"
                      type="number"
                      min="0"
                      max="6"
                      step="1"
                    />
                  </label>

                  <label class="field">
                    <span class="label">Unit label</span>
                    <InputText v-model="metricUnitLabelInput" placeholder="Optional, like lbs" />
                  </label>

                  <label v-if="metricTypeInput === 'number'" class="field">
                    <span class="label">Initial value</span>
                    <input
                      v-model="metricInitialNumberValueInput"
                      class="native-file-input"
                      type="number"
                      :step="numberInputStep(parseDecimalPlaces(metricDecimalPlacesInput))"
                    />
                  </label>

                  <label v-else class="field">
                    <span class="label">Initial value</span>
                    <input
                      v-model="metricInitialDateValueInput"
                      class="native-file-input"
                      type="date"
                    />
                  </label>

                  <Button
                    label="Create metric"
                    icon="pi pi-plus"
                    :loading="metricsStore.submissionState === 'submitting'"
                    @click="submitMetricForm"
                  />
                </div>
              </div>

              <div class="panel-card">
                <p class="panel-eyebrow">Metric history</p>
                <h2>Update tracked values</h2>
                <p>Quick-add the latest value for each metric and review the most recent history.</p>

                <label class="checkbox-row">
                  <Checkbox
                    v-model="metricsStore.includeArchived"
                    binary
                    input-id="include-archived-metrics"
                    @change="metricsStore.loadMetrics()"
                  />
                  <span>Include archived</span>
                </label>

                <div v-if="metricsStore.viewState === 'loading'" class="loading">
                  <ProgressSpinner
                    strokeWidth="5"
                    style="width: 2rem; height: 2rem"
                    animationDuration=".8s"
                  />
                  <span>Loading metrics.</span>
                </div>

                <div v-else-if="metricsStore.metrics.length === 0" class="empty-state">
                  No metrics yet.
                </div>

                <div v-else class="list-stack">
                  <article
                    v-for="metric in metricsStore.metrics"
                    :key="metric.id"
                    class="tracking-card"
                  >
                    <div class="tracking-card-header">
                      <div>
                        <h3>{{ metric.name }}</h3>
                        <p>
                          Latest:
                          {{
                            formatMetricValue(
                              metric.metric_type,
                              metric.latest_entry?.number_value ?? null,
                              metric.latest_entry?.date_value ?? null,
                              metric.decimal_places,
                            )
                          }}
                          <span v-if="metric.unit_label !== null"> {{ metric.unit_label }}</span>
                        </p>
                      </div>
                      <div class="metric-card-tags">
                        <Tag :value="metric.metric_type" severity="info" />
                        <Tag v-if="metric.is_archived" value="archived" severity="warning" />
                      </div>
                    </div>

                    <div class="metric-card-actions">
                      <Button
                        v-if="!metric.is_archived"
                        label="Archive"
                        icon="pi pi-box"
                        severity="secondary"
                        text
                        :loading="metricsStore.submissionState === 'submitting'"
                        @click="setMetricArchived(metric.id, true)"
                      />
                      <Button
                        v-else
                        label="Restore"
                        icon="pi pi-refresh"
                        severity="secondary"
                        text
                        :loading="metricsStore.submissionState === 'submitting'"
                        @click="setMetricArchived(metric.id, false)"
                      />
                      <Button
                        label="Delete"
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        :loading="metricsStore.submissionState === 'submitting'"
                        @click="deleteMetricEntry(metric.id)"
                      />
                    </div>

                    <div v-if="!metric.is_archived" class="quick-entry-grid">
                      <label v-if="metric.metric_type === 'number'" class="field">
                        <span class="label">New value</span>
                        <input
                          v-model="metricEntryNumberInputs[metric.id]"
                          class="native-file-input"
                          type="number"
                          :step="numberInputStep(metric.decimal_places)"
                        />
                      </label>

                      <label v-else class="field">
                        <span class="label">New value</span>
                        <input
                          v-model="metricEntryDateInputs[metric.id]"
                          class="native-file-input"
                          type="date"
                        />
                      </label>

                      <Button
                        label="Add update"
                        icon="pi pi-save"
                        severity="secondary"
                        :loading="metricsStore.submissionState === 'submitting'"
                        @click="submitMetricEntry(metric.id, metric.metric_type)"
                      />
                    </div>

                    <Message v-else severity="warn" :closable="false">
                      Archived metrics are hidden by default and cannot receive new updates.
                    </Message>

                    <div class="history-list">
                      <div
                        v-for="entry in metric.entries.slice(0, 3)"
                        :key="entry.id"
                        class="history-row"
                      >
                        <strong>
                          {{
                            formatMetricValue(
                              metric.metric_type,
                              entry.number_value,
                              entry.date_value,
                              metric.decimal_places,
                            )
                          }}
                        </strong>
                        <span>{{ formatDateTime(entry.recorded_at) }}</span>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </TabPanel>
          <TabPanel header="Goals">
            <div class="goals-grid">
              <div class="panel-card">
                <p class="panel-eyebrow">Goals</p>
                <h2>Create a goal</h2>
                <p>Goals reference a metric and define the time window or target you care about.</p>

                <div class="form-stack">
                  <Message v-if="goalSuccessMessage !== ''" severity="success" :closable="false">
                    {{ goalSuccessMessage }}
                  </Message>
                  <Message v-if="goalsStore.errorMessage !== ''" severity="error" :closable="false">
                    {{ goalsStore.errorMessage }}
                  </Message>

                  <label class="field">
                    <span class="label">Goal title</span>
                    <InputText v-model="goalTitleInput" />
                  </label>

                  <label class="field">
                    <span class="label">Description</span>
                    <textarea v-model="goalDescriptionInput" class="native-textarea" rows="3" />
                  </label>

                  <label class="checkbox-row">
                    <Checkbox v-model="goalUseNewMetric" binary input-id="goal-use-new-metric" />
                    <span>Create a new metric as part of this goal</span>
                  </label>

                  <template v-if="goalUseNewMetric">
                    <label class="field">
                      <span class="label">New metric name</span>
                      <InputText v-model="goalNewMetricNameInput" />
                    </label>

                    <label class="field">
                      <span class="label">New metric type</span>
                      <select v-model="goalNewMetricTypeInput" class="native-file-input">
                        <option value="number">Number</option>
                        <option value="date">Date</option>
                      </select>
                    </label>

                    <label v-if="goalNewMetricTypeInput === 'number'" class="field">
                      <span class="label">Decimal places</span>
                      <input
                        v-model="goalNewMetricDecimalPlacesInput"
                        class="native-file-input"
                        type="number"
                        min="0"
                        max="6"
                        step="1"
                      />
                    </label>

                    <label class="field">
                      <span class="label">Unit label</span>
                      <InputText
                        v-model="goalNewMetricUnitLabelInput"
                        placeholder="Optional, like lbs"
                      />
                    </label>

                    <label v-if="goalNewMetricTypeInput === 'number'" class="field">
                      <span class="label">Initial metric value</span>
                      <input
                        v-model="goalNewMetricInitialNumberValueInput"
                        class="native-file-input"
                        type="number"
                        :step="numberInputStep(parseDecimalPlaces(goalNewMetricDecimalPlacesInput))"
                      />
                    </label>

                    <label v-else class="field">
                      <span class="label">Initial metric value</span>
                      <input
                        v-model="goalNewMetricInitialDateValueInput"
                        class="native-file-input"
                        type="date"
                      />
                    </label>
                  </template>

                  <label v-else class="field">
                    <span class="label">Metric</span>
                    <select v-model="goalMetricIdInput" class="native-file-input">
                      <option
                        v-for="metric in activeMetrics"
                        :key="metric.id"
                        :value="metric.id"
                      >
                        {{ metric.name }} ({{ metric.metric_type }})
                      </option>
                    </select>
                  </label>

                  <div class="date-grid">
                    <label class="field">
                      <span class="label">Start date</span>
                      <input v-model="goalStartDateInput" class="native-file-input" type="date" />
                    </label>

                    <label class="field">
                      <span class="label">Target date</span>
                      <input v-model="goalTargetDateInput" class="native-file-input" type="date" />
                    </label>
                  </div>

                  <label v-if="goalMetricType === 'number'" class="field">
                    <span class="label">Target metric value</span>
                    <input
                      v-model="goalTargetNumberValueInput"
                      class="native-file-input"
                      type="number"
                      :step="numberInputStep(selectedGoalMetric?.decimal_places ?? parseDecimalPlaces(goalNewMetricDecimalPlacesInput))"
                    />
                  </label>

                  <label v-else class="field">
                    <span class="label">Target metric date</span>
                    <input
                      v-model="goalTargetDateValueInput"
                      class="native-file-input"
                      type="date"
                    />
                  </label>

                  <Button
                    label="Create goal"
                    icon="pi pi-flag"
                    :loading="goalsStore.submissionState === 'submitting'"
                    @click="submitGoalForm"
                  />
                </div>
              </div>

              <div class="panel-card">
                <p class="panel-eyebrow">Goal list</p>
                <h2>Current goals</h2>
                <div v-if="goalsStore.viewState === 'loading'" class="loading">
                  <ProgressSpinner
                    strokeWidth="5"
                    style="width: 2rem; height: 2rem"
                    animationDuration=".8s"
                  />
                  <span>Loading goals.</span>
                </div>

                <div v-else-if="goalsStore.goals.length === 0" class="empty-state">
                  No goals yet.
                </div>

                <div v-else class="list-stack">
                  <article v-for="goal in goalsStore.goals" :key="goal.id" class="tracking-card">
                    <div class="tracking-card-header">
                      <div>
                        <h3>{{ goal.title }}</h3>
                        <p v-if="goal.description !== null">{{ goal.description }}</p>
                      </div>
                      <Tag :value="goal.status" severity="success" />
                    </div>

                    <div class="goal-meta-grid">
                      <div class="history-row">
                        <strong>Metric</strong>
                        <span>{{ goal.metric.name }} ({{ goal.metric.metric_type }})</span>
                      </div>
                      <div class="history-row">
                        <strong>Start</strong>
                        <span>{{ goal.start_date }}</span>
                      </div>
                      <div class="history-row" v-if="goal.target_date !== null">
                        <strong>Target date</strong>
                        <span>{{ goal.target_date }}</span>
                      </div>
                      <div
                        class="history-row"
                        v-if="goal.target_value_number !== null || goal.target_value_date !== null"
                      >
                        <strong>Target value</strong>
                        <span>{{
                          goal.target_value_number !== null
                            ? formatNumberValue(goal.target_value_number, goal.metric.decimal_places)
                            : goal.target_value_date
                        }}</span>
                      </div>
                      <div class="history-row" v-if="goal.metric.latest_entry !== null">
                        <strong>Latest metric</strong>
                        <span>
                          {{
                            formatMetricValue(
                              goal.metric.metric_type,
                              goal.metric.latest_entry.number_value,
                              goal.metric.latest_entry.date_value,
                              goal.metric.decimal_places,
                            )
                          }}
                        </span>
                      </div>
                    </div>
                  </article>
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
    </section>

    <section v-else class="hero">
      <div class="hero-copy">
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

.tracking-grid {
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
.field,
.form-stack,
.list-stack,
.goal-meta-grid,
.quick-entry-grid,
.date-grid,
.history-list {
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

.empty-state {
  color: #64748b;
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

.native-textarea {
  padding: 0.8rem 0.9rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.85rem;
  background: #fff;
  font: inherit;
  resize: vertical;
}

.tracking-card {
  display: grid;
  gap: 1rem;
  padding: 1.1rem;
  border-radius: 1rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.84);
}

.tracking-card-header,
.history-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
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
.profile-dialog :deep(.full-width-input),
.profile-dialog :deep(.full-width-dropdown) {
  width: 100%;
}

.auth-card :deep(.p-password),
.profile-dialog :deep(.p-password),
.profile-dialog :deep(.p-dropdown) {
  width: 100%;
}

.auth-card :deep(.p-tabview-panels) {
  padding-inline: 0;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.15fr 1fr 0.95fr;
  }

  .tracking-grid,
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

  .tracking-card-header,
  .history-row,
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
