<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";

import type { NotificationSummary } from "../../lib/api";
import { numberInputStep, parseOptionalNumber } from "../../lib/tracking";
import {
  combineLocalDateAndTimeToIso,
  formatShortWeekdayDate,
  getBrowserTimezone,
  normalizeTimeInputValue,
} from "../../lib/time";
import { useAppToast } from "../../lib/toast";
import { useNotificationsStore } from "../../stores/notifications";

const props = defineProps<{
  notification: NotificationSummary | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  resolved: [];
  "update:visible": [value: boolean];
}>();

const notificationsStore = useNotificationsStore();
const { showSuccess } = useAppToast();

const numberValueInput = ref("");
const recordedTimeInput = ref("");

const browserTimezone = computed(() => getBrowserTimezone());
const metric = computed(() => props.notification?.metric ?? null);
const notificationDateLabel = computed(() => {
  return props.notification === null ? "" : formatShortWeekdayDate(props.notification.notification_date);
});
const usesFailureUpdateType = computed(() => metric.value?.update_type === "failure");

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.notification !== null) {
      numberValueInput.value = "";
      recordedTimeInput.value = normalizeTimeInputValue(props.notification.scheduled_time);
      return;
    }

    if (!visible) {
      numberValueInput.value = "";
      recordedTimeInput.value = "";
    }
  },
  { immediate: true },
);

function buildRecordedAt(): string | null {
  if (props.notification === null || recordedTimeInput.value === "") {
    return null;
  }
  return combineLocalDateAndTimeToIso(props.notification.notification_date, recordedTimeInput.value);
}

async function submitNumberMetric(): Promise<void> {
  if (props.notification === null) {
    return;
  }

  const updated = await notificationsStore.completeNotification(
    props.notification.id,
    {
      number_value: parseOptionalNumber(numberValueInput.value),
      recorded_at: buildRecordedAt(),
      timezone: browserTimezone.value,
    },
    browserTimezone.value,
  );
  if (!updated) {
    return;
  }

  showSuccess("Metric updated from reminder.", "Notifications");
  emit("resolved");
  emit("update:visible", false);
}

async function confirmDateMetric(): Promise<void> {
  if (props.notification === null) {
    return;
  }

  const updated = await notificationsStore.completeNotification(
    props.notification.id,
    {
      recorded_at: buildRecordedAt(),
      timezone: browserTimezone.value,
    },
    browserTimezone.value,
  );
  if (!updated) {
    return;
  }

  showSuccess("Date acknowledged.", "Notifications");
  emit("resolved");
  emit("update:visible", false);
}

async function skipReminder(): Promise<void> {
  if (props.notification === null) {
    return;
  }

  const skipped = await notificationsStore.skipNotification(props.notification.id, browserTimezone.value);
  if (!skipped) {
    return;
  }

  showSuccess("Reminder cleared.", "Notifications");
  emit("resolved");
  emit("update:visible", false);
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Quick update"
    class="profile-dialog notification-entry-dialog"
    :style="{ width: 'min(30rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div v-if="notification !== null && metric !== null" class="dialog-stack">
      <section class="dialog-section">
        <div class="section-heading-text">
          <div class="notification-date-pill">{{ notificationDateLabel }}</div>
          <h3>{{ metric.name }}</h3>
        </div>

        <label class="field">
          <span class="label">Time</span>
          <input v-model="recordedTimeInput" class="native-file-input" type="time" />
        </label>

        <label v-if="metric.metric_type === 'number'" class="field">
          <span class="label">Value</span>
          <input
            v-model="numberValueInput"
            class="native-file-input"
            type="number"
            :step="numberInputStep(metric.decimal_places)"
          />
        </label>

        <div v-if="metric.metric_type === 'number'" class="dialog-actions-row">
          <Button label="Skip" severity="secondary" text @click="void skipReminder()" />
          <Button
            label="Submit"
            icon="pi pi-save"
            :loading="notificationsStore.submissionState === 'submitting'"
            @click="void submitNumberMetric()"
          />
        </div>

        <div v-else class="dialog-actions-row">
          <Button
            label="No"
            :severity="usesFailureUpdateType ? undefined : 'secondary'"
            @click="void skipReminder()"
          />
          <Button
            label="Yes"
            :severity="usesFailureUpdateType ? 'secondary' : undefined"
            :loading="notificationsStore.submissionState === 'submitting'"
            @click="void confirmDateMetric()"
          />
        </div>
      </section>
    </div>
  </Dialog>
</template>

<style scoped>
.notification-date-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-pill);
  background: var(--color-surface-muted);
  color: var(--color-text-subtle);
  font-size: var(--font-size-caption);
  font-weight: 600;
}

.dialog-actions-row {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

@media (max-width: 720px) {
  .dialog-actions-row {
    justify-content: stretch;
  }

  .dialog-actions-row :deep(.p-button) {
    flex: 1 1 0;
    justify-content: center;
  }
}
</style>
