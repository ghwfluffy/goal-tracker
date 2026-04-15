<script setup lang="ts">
import { computed } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";

import type { MetricSummary } from "../../lib/api";
import { formatShortWeekdayDate, getBrowserTimezone } from "../../lib/time";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import { useNotificationsStore } from "../../stores/notifications";

const props = defineProps<{
  decisionDate: string | null;
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

const dateLabel = computed(() => {
  return props.decisionDate === null ? "" : formatShortWeekdayDate(props.decisionDate);
});
const usesFailureUpdateType = computed(() => props.metric?.update_type === "failure");

async function submitDecision(decision: "yes" | "no"): Promise<void> {
  if (props.metric === null || props.decisionDate === null) {
    return;
  }

  const updated = await metricsStore.recordDateMetricDecision(props.metric.id, {
    decision,
    decision_date: props.decisionDate,
  });
  if (!updated) {
    return;
  }

  await Promise.all([
    goalsStore.loadGoals(),
    notificationsStore.loadNotifications(getBrowserTimezone()),
  ]);
  showSuccess("Date updated.", "Metrics");
  emit("saved");
  emit("update:visible", false);
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Update day"
    class="profile-dialog notification-entry-dialog"
    :style="{ width: 'min(30rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div v-if="metric !== null && decisionDate !== null" class="dialog-stack">
      <section class="dialog-section">
        <div class="section-heading-text">
          <div class="notification-date-pill">{{ dateLabel }}</div>
          <h3>{{ metric.name }}</h3>
        </div>

        <div class="dialog-actions-row">
          <Button
            label="No"
            :severity="usesFailureUpdateType ? undefined : 'secondary'"
            @click="void submitDecision('no')"
          />
          <Button
            label="Yes"
            :severity="usesFailureUpdateType ? 'secondary' : undefined"
            :loading="metricsStore.submissionState === 'submitting'"
            @click="void submitDecision('yes')"
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
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
