<script setup lang="ts">
import { computed, ref } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";

import type { MetricSummary } from "../../lib/api";
import { formatDateTime, formatMetricValue } from "../../lib/tracking";
import { getBrowserTimezone } from "../../lib/time";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import { useNotificationsStore } from "../../stores/notifications";
import MetricHistoryChart from "../MetricHistoryChart.vue";
import MetricHistoryEntryEditDialog from "./MetricHistoryEntryEditDialog.vue";

const props = defineProps<{
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

const metricHistoryTabIndex = ref(0);
const editingEntryId = ref("");
const editDialogVisible = ref(false);

const currentValueText = computed(() => {
  if (props.metric === null) {
    return "No value yet";
  }

  return formatMetricValue(
    props.metric.metric_type,
    props.metric.latest_entry?.number_value ?? null,
    props.metric.latest_entry?.date_value ?? null,
    props.metric.decimal_places,
  );
});

const editingEntry = computed(() => {
  if (props.metric === null || editingEntryId.value === "") {
    return null;
  }
  return props.metric.entries.find((entry) => entry.id === editingEntryId.value) ?? null;
});

function openEditDialog(entryId: string): void {
  editingEntryId.value = entryId;
  editDialogVisible.value = true;
}

async function deleteEntry(entryId: string): Promise<void> {
  if (props.metric === null) {
    return;
  }

  const confirmed = window.confirm("Delete this metric history value?");
  if (!confirmed) {
    return;
  }

  const deleted = await metricsStore.deleteMetricEntry(props.metric.id, entryId);
  if (!deleted) {
    return;
  }

  await notificationsStore.loadNotifications(getBrowserTimezone());
  await goalsStore.loadGoals();
  showSuccess("Metric value deleted.", "Metrics");
  emit("updated");
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Metric history"
    class="profile-dialog"
    :style="{ width: 'min(56rem, 96vw)' }"
    @update:visible="(value) => emit('update:visible', value)"
  >
    <div v-if="metric !== null" class="dialog-stack">
      <section class="dialog-section">
        <div class="section-heading-text">
          <h3>{{ metric.name }}</h3>
          <p>
            Current value:
            <strong>{{ currentValueText }}</strong>
            <span v-if="metric.unit_label !== null">
              {{ metric.unit_label }}
            </span>
          </p>
        </div>

        <TabView v-model:activeIndex="metricHistoryTabIndex">
          <TabPanel header="Graph">
            <MetricHistoryChart :metric="metric" />
          </TabPanel>
          <TabPanel header="Values">
            <div v-if="metric.entries.length === 0" class="empty-state">
              No history recorded yet.
            </div>
            <div v-else class="metric-history-table-wrap">
              <table class="metric-history-table">
                <thead>
                  <tr>
                    <th>Value</th>
                    <th>Recorded</th>
                    <th class="actions-column">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in metric.entries" :key="entry.id">
                    <td>
                      {{
                        formatMetricValue(
                          metric.metric_type,
                          entry.number_value,
                          entry.date_value,
                          metric.decimal_places,
                        )
                      }}
                      <span v-if="metric.unit_label !== null">
                        {{ metric.unit_label }}
                      </span>
                    </td>
                    <td>{{ formatDateTime(entry.recorded_at) }}</td>
                    <td class="actions-cell">
                      <Button
                        icon="pi pi-pencil"
                        text
                        rounded
                        severity="secondary"
                        aria-label="Edit metric value"
                        :disabled="metricsStore.submissionState === 'submitting'"
                        @click="openEditDialog(entry.id)"
                      />
                      <Button
                        icon="pi pi-trash"
                        text
                        rounded
                        severity="danger"
                        aria-label="Delete metric value"
                        :disabled="metricsStore.submissionState === 'submitting'"
                        @click="void deleteEntry(entry.id)"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </TabPanel>
        </TabView>
      </section>
    </div>

    <MetricHistoryEntryEditDialog
      v-model:visible="editDialogVisible"
      :entry="editingEntry"
      :metric="metric"
      @updated="emit('updated')"
    />
  </Dialog>
</template>

<style scoped>
.profile-dialog :deep(.p-dialog-content) {
  padding-top: 0.25rem;
}

.profile-dialog :deep(.p-tabview-panels) {
  padding-inline: 0;
}

.empty-state {
  color: var(--color-text-faint);
}

.metric-history-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border-soft);
  border-radius: var(--radius-lg);
  background: var(--color-surface-panel-subtle);
}

.metric-history-table {
  width: 100%;
  border-collapse: collapse;
}

.metric-history-table th,
.metric-history-table td {
  padding: var(--space-5) var(--space-6);
  text-align: left;
  border-bottom: 1px solid var(--color-border-soft-muted);
}

.metric-history-table th {
  font-size: var(--font-size-caption);
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-faint);
  background: var(--color-surface-muted);
}

.metric-history-table tbody tr:last-child td {
  border-bottom: 0;
}

.actions-column {
  width: 1%;
  white-space: nowrap;
}

.actions-cell {
  white-space: nowrap;
}
</style>
