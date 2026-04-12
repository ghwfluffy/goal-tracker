<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import DashboardWorkspace from "../components/DashboardWorkspace.vue";
import AppTabsShell from "../components/home/AppTabsShell.vue";
import GoalsTab from "../components/home/GoalsTab.vue";
import GuestHomePanel from "../components/home/GuestHomePanel.vue";
import HomeHeaderBanner from "../components/home/HomeHeaderBanner.vue";
import HomeProfileDialogs from "../components/home/HomeProfileDialogs.vue";
import MetricEntryDialog from "../components/home/MetricEntryDialog.vue";
import MetricHistoryDialog from "../components/home/MetricHistoryDialog.vue";
import MetricsTab from "../components/home/MetricsTab.vue";
import { watchToastError } from "../lib/toast";
import { useAuthStore } from "../stores/auth";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";
import { useMetricsStore } from "../stores/metrics";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const dashboardsStore = useDashboardsStore();
const goalsStore = useGoalsStore();
const metricsStore = useMetricsStore();
const statusStore = useStatusStore();

const activeTabIndex = ref(0);
const profileVisible = ref(false);
const passwordVisible = ref(false);
const deleteAccountVisible = ref(false);
const invitationCodesVisible = ref(false);
const metricHistoryVisible = ref(false);
const metricHistoryMetricId = ref("");
const metricEntryVisible = ref(false);
const metricEntryMetricId = ref("");

const tabs = [
  { key: "dashboards", label: "Dashboards" },
  { key: "metrics", label: "Metrics" },
  { key: "goals", label: "Goals" },
];

const appVersion = computed(() => {
  return statusStore.state === "ready" && statusStore.data !== null ? statusStore.data.version : null;
});

const selectedMetricHistory = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === metricHistoryMetricId.value) ?? null;
});

const selectedMetricEntry = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === metricEntryMetricId.value) ?? null;
});

watchToastError(() => authStore.errorMessage, "Authentication");
watchToastError(() => dashboardsStore.errorMessage, "Dashboards");
watchToastError(() => goalsStore.errorMessage, "Goals");
watchToastError(() => metricsStore.errorMessage, "Metrics");

async function loadTrackingData(): Promise<void> {
  await Promise.all([
    dashboardsStore.loadDashboards(),
    metricsStore.loadMetrics(),
    goalsStore.loadGoals(),
  ]);
}

function openMetricHistory(metricId: string): void {
  metricHistoryMetricId.value = metricId;
  metricHistoryVisible.value = true;
}

function openMetricEntry(metricId: string): void {
  metricEntryMetricId.value = metricId;
  metricEntryVisible.value = true;
}

watch(
  () => authStore.currentUser,
  async (currentUser) => {
    if (currentUser !== null) {
      await loadTrackingData();
      return;
    }

    dashboardsStore.reset();
    metricsStore.reset();
    goalsStore.reset();
    profileVisible.value = false;
    passwordVisible.value = false;
    deleteAccountVisible.value = false;
    invitationCodesVisible.value = false;
    metricHistoryVisible.value = false;
    metricEntryVisible.value = false;
    metricHistoryMetricId.value = "";
    metricEntryMetricId.value = "";
  },
  { immediate: true },
);

watch(
  () => metricsStore.metrics,
  () => {
    if (
      metricHistoryMetricId.value !== "" &&
      metricsStore.metrics.every((metric) => metric.id !== metricHistoryMetricId.value)
    ) {
      metricHistoryVisible.value = false;
      metricHistoryMetricId.value = "";
    }

    if (
      metricEntryMetricId.value !== "" &&
      metricsStore.metrics.every((metric) => metric.id !== metricEntryMetricId.value)
    ) {
      metricEntryVisible.value = false;
      metricEntryMetricId.value = "";
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
    <section v-if="authStore.isAuthenticated && authStore.currentUser !== null" class="app-shell">
      <HomeHeaderBanner
        :user="authStore.currentUser"
        :version="appVersion"
        @open-profile="profileVisible = true"
        @open-password="passwordVisible = true"
        @open-invitation-codes="invitationCodesVisible = true"
        @delete-account="deleteAccountVisible = true"
        @logout="void authStore.logout()"
      />

      <AppTabsShell v-model:activeIndex="activeTabIndex" :tabs="tabs">
        <template #dashboards>
          <DashboardWorkspace />
        </template>
        <template #metrics>
          <MetricsTab
            @open-metric-entry="openMetricEntry"
            @open-metric-history="openMetricHistory"
          />
        </template>
        <template #goals>
          <GoalsTab
            @open-metric-entry="openMetricEntry"
            @open-metric-history="openMetricHistory"
          />
        </template>
      </AppTabsShell>

      <MetricHistoryDialog
        v-model:visible="metricHistoryVisible"
        :metric="selectedMetricHistory"
      />
      <MetricEntryDialog
        v-model:visible="metricEntryVisible"
        :metric="selectedMetricEntry"
      />
      <HomeProfileDialogs
        v-model:profileVisible="profileVisible"
        v-model:passwordVisible="passwordVisible"
        v-model:deleteAccountVisible="deleteAccountVisible"
        v-model:invitationCodesVisible="invitationCodesVisible"
      />
    </section>

    <GuestHomePanel v-else />
  </main>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: 1.5rem;
}

.app-shell {
  max-width: 1180px;
  margin: 0 auto;
}

@media (max-width: 720px) {
  .home-view {
    padding: 1rem;
  }
}
</style>
