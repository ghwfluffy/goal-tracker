<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";

import type { MetricEntrySummary, MetricSummary } from "../../lib/api";
import { combineLocalDateAndTimeToIso, getBrowserTimezone } from "../../lib/time";
import { isNumericMetricType, numberInputStep, parseOptionalNumber } from "../../lib/tracking";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import { useNotificationsStore } from "../../stores/notifications";

const props = defineProps<{
  entry: MetricEntrySummary | null;
  metric: MetricSummary | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  updated: [];
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

const valueLabel = computed(() => {
  if (props.metric?.metric_type === "count") {
    return "Total value";
  }
  return "Value";
});

watch(
  [() => props.visible, () => props.metric, () => props.entry],
  ([visible, metric, entry]) => {
    if (visible && metric !== null && entry !== null) {
      const localInputs = toLocalInputs(entry.recorded_at);
      numberValueInput.value = entry.number_value !== null ? String(entry.number_value) : "";
      dateValueInput.value = entry.date_value ?? "";
      recordedDateInput.value = localInputs.date;
      recordedTimeInput.value = localInputs.time;
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

async function submit(): Promise<void> {
  if (props.metric === null || props.entry === null) {
    return;
  }

  const updated = await metricsStore.updateMetricEntry(props.metric.id, props.entry.id, {
    date_value: props.metric.metric_type === "date" ? dateValueInput.value || null : null,
    number_value: isNumericMetricType(props.metric.metric_type) ? parseOptionalNumber(numberValueInput.value) : null,
    recorded_at: buildRecordedAt(),
  });

  if (!updated) {
    return;
  }

  await notificationsStore.loadNotifications(getBrowserTimezone());
  await goalsStore.loadGoals();
  showSuccess("Metric value updated.", "Metrics");
  emit("updated");
  emit("update:visible", false);
}

function buildRecordedAt(): string | null {
  if (recordedDateInput.value === "" || recordedTimeInput.value === "") {
    return null;
  }
  return combineLocalDateAndTimeToIso(recordedDateInput.value, recordedTimeInput.value);
}

function toLocalInputs(value: string): { date: string; time: string } {
  const timestamp = new Date(value);
  return {
    date: `${timestamp.getFullYear()}-${String(timestamp.getMonth() + 1).padStart(2, "0")}-${String(timestamp.getDate()).padStart(2, "0")}`,
    time: `${String(timestamp.getHours()).padStart(2, "0")}:${String(timestamp.getMinutes()).padStart(2, "0")}`,
  };
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Edit metric value"
    class="profile-dialog"
    :style="{ width: 'min(30rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div class="dialog-stack">
      <section v-if="metric !== null && entry !== null" class="dialog-section">
        <div class="section-heading-text">
          <h3>{{ metric.name }}</h3>
          <p>Edit the selected history entry.</p>
        </div>

        <label v-if="isNumericMetricType(metric.metric_type)" class="field">
          <span class="label">{{ valueLabel }}</span>
          <input
            v-model="numberValueInput"
            class="native-file-input"
            type="number"
            :step="numberInputStep(metric.decimal_places)"
          />
        </label>

        <label v-else class="field">
          <span class="label">{{ valueLabel }}</span>
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
            label="Save changes"
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
