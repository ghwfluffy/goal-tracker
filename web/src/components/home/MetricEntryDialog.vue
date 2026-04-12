<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";

import type { MetricSummary } from "../../lib/api";
import { numberInputStep, parseOptionalNumber } from "../../lib/tracking";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";

const props = defineProps<{
  metric: MetricSummary | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  saved: [];
  "update:visible": [value: boolean];
}>();

const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();
const { showSuccess } = useAppToast();

const numberValueInput = ref("");
const dateValueInput = ref("");

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      numberValueInput.value = "";
      dateValueInput.value = "";
    }
  },
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
  });

  if (!updated) {
    return;
  }

  showSuccess("Metric updated.", "Metrics");
  await goalsStore.loadGoals();
  emit("saved");
  emit("update:visible", false);
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
.dialog-stack,
.dialog-section,
.field {
  display: grid;
  gap: 1rem;
}

.section-heading-text h3 {
  margin: 0;
  font-size: 1.1rem;
}

.section-heading-text p {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  color: #334155;
}

.dialog-actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

@media (max-width: 720px) {
  .dialog-actions-row {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
