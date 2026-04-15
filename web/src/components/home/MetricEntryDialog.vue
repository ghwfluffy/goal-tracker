<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";

import type { MetricSummary } from "../../lib/api";
import {
  combineLocalDateAndTimeToIso,
  getBrowserTimezone,
  getCurrentDateInTimezone,
  getCurrentTimeInputValue,
} from "../../lib/time";
import { numberInputStep, parseOptionalNumber } from "../../lib/tracking";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import { useNotificationsStore } from "../../stores/notifications";

const props = defineProps<{
  initialDateValue?: string | null;
  initialRecordedDate?: string | null;
  metric: MetricSummary | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  saved: [];
  "update:visible": [value: boolean];
}>();

const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();
const notificationsStore = useNotificationsStore();
const { showSuccess } = useAppToast();

const numberValueInput = ref("");
const dateValueInput = ref("");
const recordedDateInput = ref("");
const recordedTimeInput = ref("");

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.metric !== null) {
      const now = new Date();
      const defaultDate =
        props.initialRecordedDate ?? getCurrentDateInTimezone(getBrowserTimezone(), now);
      numberValueInput.value = "";
      dateValueInput.value =
        props.metric.metric_type === "date"
          ? (props.initialDateValue ?? "")
          : "";
      recordedDateInput.value = defaultDate;
      recordedTimeInput.value = getCurrentTimeInputValue(now);
      return;
    }

    if (!visible) {
      numberValueInput.value = "";
      dateValueInput.value = "";
      recordedDateInput.value = "";
      recordedTimeInput.value = "";
    }
  },
  { immediate: true },
);

const dialogTitle = computed(() => {
  return props.metric === null ? "Add metric update" : props.metric.name;
});

async function submit(): Promise<void> {
  if (props.metric === null) {
    return;
  }

  const updated = await metricsStore.addMetricEntry(props.metric.id, {
    date_value: props.metric.metric_type === "date" ? dateValueInput.value || null : null,
    number_value: props.metric.metric_type === "number" ? parseOptionalNumber(numberValueInput.value) : null,
    recorded_at: buildRecordedAt(),
  });

  if (!updated) {
    return;
  }

  await notificationsStore.loadNotifications(getBrowserTimezone());
  showSuccess("Metric updated.", "Metrics");
  await goalsStore.loadGoals();
  emit("saved");
  emit("update:visible", false);
}

function buildRecordedAt(): string | null {
  if (recordedDateInput.value === "" || recordedTimeInput.value === "") {
    return null;
  }
  return combineLocalDateAndTimeToIso(recordedDateInput.value, recordedTimeInput.value);
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Add metric update"
    class="profile-dialog"
    :style="{ width: 'min(30rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div class="dialog-stack">
      <section v-if="metric !== null" class="dialog-section">
        <div class="section-heading-text">
          <h3>{{ dialogTitle }}</h3>
          <p>Record the next value for this metric.</p>
        </div>

        <label v-if="metric.metric_type === 'number'" class="field">
          <span class="label">New value</span>
          <input
            v-model="numberValueInput"
            class="native-file-input"
            type="number"
            :step="numberInputStep(metric.decimal_places)"
          />
        </label>

        <label v-else class="field">
          <span class="label">New value</span>
          <input
            v-model="dateValueInput"
            class="native-file-input"
            type="date"
          />
        </label>

        <label class="field">
          <span class="label">Recorded date</span>
          <input v-model="recordedDateInput" class="native-file-input" type="date" />
        </label>

        <label class="field">
          <span class="label">Recorded time</span>
          <input v-model="recordedTimeInput" class="native-file-input" type="time" />
        </label>

        <div class="dialog-actions-row">
          <Button
            label="Cancel"
            severity="secondary"
            text
            @click="emit('update:visible', false)"
          />
          <Button
            label="Save update"
            icon="pi pi-save"
            :loading="metricsStore.submissionState === 'submitting'"
            @click="submit"
          />
        </div>
      </section>
    </div>
  </Dialog>
</template>

<style scoped>
.dialog-actions-row {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-4);
}

@media (max-width: 720px) {
  .dialog-actions-row {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
