<script setup lang="ts">
import { computed, ref } from "vue";
import Dialog from "primevue/dialog";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";

import type { MetricSummary } from "../../lib/api";
import { formatDateTime, formatMetricValue } from "../../lib/tracking";
import MetricHistoryChart from "../MetricHistoryChart.vue";

const props = defineProps<{
  metric: MetricSummary | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const metricHistoryTabIndex = ref(0);

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
                  </tr>
                </tbody>
              </table>
            </div>
          </TabPanel>
        </TabView>
      </section>
    </div>
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
</style>
