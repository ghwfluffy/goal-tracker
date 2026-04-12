<script setup lang="ts">
import Dialog from "primevue/dialog";
import ProgressSpinner from "primevue/progressspinner";

import type { NotificationSummary } from "../../lib/api";
import { formatShortWeekdayDate } from "../../lib/time";

defineProps<{
  notifications: NotificationSummary[];
  visible: boolean;
  viewState: "idle" | "loading" | "ready" | "error";
}>();

const emit = defineEmits<{
  openNotification: [notificationId: string];
  "update:visible": [value: boolean];
}>();
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Notifications"
    class="profile-dialog notifications-dialog"
    :style="{ width: 'min(32rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div class="dialog-stack notifications-shell">
      <div v-if="viewState === 'loading'" class="panel-card loading">
        <ProgressSpinner strokeWidth="5" style="width: 2rem; height: 2rem" animationDuration=".8s" />
        <span>Loading notifications.</span>
      </div>

      <div v-else-if="notifications.length === 0" class="panel-card empty-state">
        Nothing needs updating right now.
      </div>

      <template v-else>
        <button
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-card"
          type="button"
          @click="emit('openNotification', notification.id)"
        >
          <div class="notification-card-header">
            <strong>{{ notification.metric.name }}</strong>
            <span>{{ notification.scheduled_time }}</span>
          </div>
          <div class="notification-card-meta">
            <span>{{ formatShortWeekdayDate(notification.notification_date) }}</span>
            <span>{{ notification.metric.metric_type === "number" ? "Enter value" : "Confirm yes or no" }}</span>
          </div>
        </button>
      </template>
    </div>
  </Dialog>
</template>

<style scoped>
.notifications-shell {
  gap: var(--space-3);
}

.notification-card {
  width: 100%;
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  text-align: left;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-soft);
  background: var(--color-surface-panel-strong);
  color: var(--color-text-default);
}

.notification-card-header,
.notification-card-meta {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: center;
}

.notification-card-meta {
  color: var(--color-text-subtle);
  font-size: var(--font-size-caption);
}

@media (max-width: 720px) {
  .notification-card-header,
  .notification-card-meta {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
