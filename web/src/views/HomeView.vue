<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import DashboardWorkspace from "../components/DashboardWorkspace.vue";
import AppTabsShell from "../components/home/AppTabsShell.vue";
import GoalsTab from "../components/home/GoalsTab.vue";
import GuestHomePanel from "../components/home/GuestHomePanel.vue";
import HomeHeaderBanner from "../components/home/HomeHeaderBanner.vue";
import HomeNotificationsDialog from "../components/home/HomeNotificationsDialog.vue";
import HomeProfileDialogs from "../components/home/HomeProfileDialogs.vue";
import MetricEntryDialog from "../components/home/MetricEntryDialog.vue";
import MetricHistoryDialog from "../components/home/MetricHistoryDialog.vue";
import MetricsTab from "../components/home/MetricsTab.vue";
import NotificationEntryDialog from "../components/home/NotificationEntryDialog.vue";
import { getBrowserTimezone } from "../lib/time";
import { watchToastError } from "../lib/toast";
import { useAuthStore } from "../stores/auth";
import { useBackupsStore } from "../stores/backups";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";
import { useMetricsStore } from "../stores/metrics";
import { useNotificationsStore } from "../stores/notifications";
import { useShareLinksStore } from "../stores/shareLinks";
import { useStatusStore } from "../stores/status";

const authStore = useAuthStore();
const backupsStore = useBackupsStore();
const dashboardsStore = useDashboardsStore();
const goalsStore = useGoalsStore();
const metricsStore = useMetricsStore();
const notificationsStore = useNotificationsStore();
const shareLinksStore = useShareLinksStore();
const statusStore = useStatusStore();

const activeTabIndex = ref(0);
const profileVisible = ref(false);
const passwordVisible = ref(false);
const deleteAccountVisible = ref(false);
const backupsVisible = ref(false);
const invitationCodesVisible = ref(false);
const sharedLinksVisible = ref(false);
const notificationsVisible = ref(false);
const notificationEntryVisible = ref(false);
const notificationEntryId = ref("");
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
  return statusStore.state === "ready" && statusStore.data !== null
    ? statusStore.data.version
    : null;
});

const selectedMetricHistory = computed(() => {
  return (
    metricsStore.metrics.find(
      (metric) => metric.id === metricHistoryMetricId.value,
    ) ?? null
  );
});

const selectedMetricEntry = computed(() => {
  return (
    metricsStore.metrics.find(
      (metric) => metric.id === metricEntryMetricId.value,
    ) ?? null
  );
});

const selectedNotificationEntry = computed(() => {
  return (
    notificationsStore.notifications.find(
      (notification) => notification.id === notificationEntryId.value,
    ) ?? null
  );
});

let notificationsRefreshTimer: number | null = null;

watchToastError(() => authStore.errorMessage, "Authentication");
watchToastError(() => backupsStore.errorMessage, "Backups");
watchToastError(() => dashboardsStore.errorMessage, "Dashboards");
watchToastError(() => goalsStore.errorMessage, "Goals");
watchToastError(() => metricsStore.errorMessage, "Metrics");
watchToastError(() => notificationsStore.errorMessage, "Notifications");
watchToastError(() => shareLinksStore.errorMessage, "Shared links");

async function loadTrackingData(): Promise<void> {
  await Promise.all([
    dashboardsStore.loadDashboards(),
    metricsStore.loadMetrics(),
    goalsStore.loadGoals(),
    notificationsStore.loadNotifications(getBrowserTimezone()),
  ]);
}

async function refreshDependentTrackingViews(): Promise<void> {
  await Promise.all([
    dashboardsStore.loadDashboards(),
    goalsStore.loadGoals(),
    notificationsStore.loadNotifications(getBrowserTimezone()),
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

function openNotificationEntry(notificationId: string): void {
  notificationEntryId.value = notificationId;
  notificationEntryVisible.value = true;
}

function restartNotificationsRefreshTimer(): void {
  if (notificationsRefreshTimer !== null) {
    window.clearInterval(notificationsRefreshTimer);
    notificationsRefreshTimer = null;
  }

  if (authStore.currentUser === null) {
    return;
  }

  notificationsRefreshTimer = window.setInterval(() => {
    void notificationsStore.loadNotifications(getBrowserTimezone());
  }, 60_000);
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
    notificationsStore.reset();
    shareLinksStore.reset();
    profileVisible.value = false;
    passwordVisible.value = false;
    deleteAccountVisible.value = false;
    backupsVisible.value = false;
    invitationCodesVisible.value = false;
    sharedLinksVisible.value = false;
    notificationsVisible.value = false;
    notificationEntryVisible.value = false;
    metricHistoryVisible.value = false;
    metricEntryVisible.value = false;
    notificationEntryId.value = "";
    metricHistoryMetricId.value = "";
    metricEntryMetricId.value = "";
  },
  { immediate: true },
);

watch(
  () => authStore.currentUser,
  () => {
    restartNotificationsRefreshTimer();
  },
  { immediate: true },
);

watch(
  () => metricsStore.metrics,
  () => {
    if (authStore.currentUser !== null) {
      void notificationsStore.loadNotifications(getBrowserTimezone());
    }

    if (
      metricHistoryMetricId.value !== "" &&
      metricsStore.metrics.every(
        (metric) => metric.id !== metricHistoryMetricId.value,
      )
    ) {
      metricHistoryVisible.value = false;
      metricHistoryMetricId.value = "";
    }

    if (
      metricEntryMetricId.value !== "" &&
      metricsStore.metrics.every(
        (metric) => metric.id !== metricEntryMetricId.value,
      )
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

watch(
  () => notificationsStore.notifications,
  () => {
    if (
      notificationEntryId.value !== "" &&
      notificationsStore.notifications.every(
        (notification) => notification.id !== notificationEntryId.value,
      )
    ) {
      notificationEntryVisible.value = false;
      notificationEntryId.value = "";
    }
  },
  { deep: true },
);

onBeforeUnmount(() => {
  if (notificationsRefreshTimer !== null) {
    window.clearInterval(notificationsRefreshTimer);
  }
});
</script>

<template>
  <main
    :class="[
      'home-view',
      { 'home-view--guest': !(authStore.isAuthenticated && authStore.currentUser !== null) },
    ]"
  >
    <section
      v-if="authStore.isAuthenticated && authStore.currentUser !== null"
      class="app-shell"
    >
      <HomeHeaderBanner
        :notification-count="notificationsStore.count"
        :user="authStore.currentUser"
        :version="appVersion"
        @open-notifications="notificationsVisible = true"
        @open-profile="profileVisible = true"
        @open-password="passwordVisible = true"
        @open-shared-links="sharedLinksVisible = true"
        @open-backups="backupsVisible = true"
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
      <HomeNotificationsDialog
        v-model:visible="notificationsVisible"
        :notifications="notificationsStore.notifications"
        :view-state="notificationsStore.viewState"
        @open-notification="openNotificationEntry"
      />
      <MetricEntryDialog
        v-model:visible="metricEntryVisible"
        :metric="selectedMetricEntry"
        @saved="void refreshDependentTrackingViews()"
      />
      <NotificationEntryDialog
        v-model:visible="notificationEntryVisible"
        :notification="selectedNotificationEntry"
        @resolved="void refreshDependentTrackingViews()"
      />
      <HomeProfileDialogs
        v-model:profileVisible="profileVisible"
        v-model:passwordVisible="passwordVisible"
        v-model:deleteAccountVisible="deleteAccountVisible"
        v-model:backupsVisible="backupsVisible"
        v-model:invitationCodesVisible="invitationCodesVisible"
        v-model:sharedLinksVisible="sharedLinksVisible"
      />
    </section>

    <GuestHomePanel v-else />
  </main>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: var(--space-9);
}

.home-view--guest {
  padding: 0;
}

.app-shell {
  max-width: 1180px;
  margin: 0 auto;
}

@media (max-width: 720px) {
  .home-view {
    padding: 0;
  }
}
</style>
