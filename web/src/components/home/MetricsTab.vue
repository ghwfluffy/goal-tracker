<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import { numberInputStep, parseDecimalPlaces, parseOptionalNumber } from "../../lib/tracking";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import ManagementToolbar from "./ManagementToolbar.vue";

const emit = defineEmits<{
  openMetricEntry: [metricId: string];
  openMetricHistory: [metricId: string];
}>();

const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();

const metricRowMenu = ref<InstanceType<typeof Menu> | null>(null);
const activeMetricMenuId = ref("");
const createDialogVisible = ref(false);
const viewMode = ref<"table" | "cards">("table");

const metricNameInput = ref("");
const metricTypeInput = ref<"number" | "date">("number");
const metricDecimalPlacesInput = ref("0");
const metricUnitLabelInput = ref("");
const metricInitialNumberValueInput = ref("");
const metricInitialDateValueInput = ref("");
const { showSuccess } = useAppToast();

const selectedMetricMenuMetric = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === activeMetricMenuId.value) ?? null;
});

const metricRowMenuItems = computed<MenuItem[]>(() => {
  const metric = selectedMetricMenuMetric.value;
  if (metric === null) {
    return [];
  }

  const items: MenuItem[] = [];

  if (!metric.is_archived) {
    items.push({
      icon: "pi pi-plus-circle",
      label: "Add update",
      command: () => emit("openMetricEntry", metric.id),
    });
  }

  items.push({
    icon: "pi pi-chart-line",
    label: "View history",
    command: () => emit("openMetricHistory", metric.id),
  });

  items.push(
    metric.is_archived
      ? {
          icon: "pi pi-refresh",
          label: "Restore",
          command: () => {
            void setMetricArchived(metric.id, false);
          },
        }
      : {
          icon: "pi pi-box",
          label: "Archive",
          command: () => {
            void setMetricArchived(metric.id, true);
          },
        },
  );

  items.push({
    icon: "pi pi-trash",
    label: "Delete",
    command: () => {
      void deleteMetricEntry(metric.id);
    },
  });

  return items;
});

function resetMetricForm(): void {
  metricNameInput.value = "";
  metricTypeInput.value = "number";
  metricDecimalPlacesInput.value = "0";
  metricUnitLabelInput.value = "";
  metricInitialNumberValueInput.value = "";
  metricInitialDateValueInput.value = "";
}

function openCreateDialog(): void {
  resetMetricForm();
  createDialogVisible.value = true;
}

function toggleMetricRowMenu(event: Event, metricId: string): void {
  activeMetricMenuId.value = metricId;
  metricRowMenu.value?.toggle(event);
}

function formatMetricLatestSummary(metric: (typeof metricsStore.metrics)[number]): string {
  const latestEntry = metric.latest_entry;
  if (latestEntry === null) {
    return "No value yet";
  }

  if (metric.metric_type === "date") {
    return latestEntry.date_value ?? "No value yet";
  }

  const numberValue = latestEntry.number_value;
  if (numberValue === null) {
    return "No value yet";
  }

  const formatted = numberValue.toFixed(metric.decimal_places ?? 0);
  return metric.unit_label === null ? formatted : `${formatted} ${metric.unit_label}`;
}

async function submitMetricForm(): Promise<void> {
  const created = await metricsStore.createMetric({
    decimal_places:
      metricTypeInput.value === "number" ? parseDecimalPlaces(metricDecimalPlacesInput.value) : null,
    initial_date_value:
      metricTypeInput.value === "date" ? metricInitialDateValueInput.value || null : null,
    initial_number_value:
      metricTypeInput.value === "number" ? parseOptionalNumber(metricInitialNumberValueInput.value) : null,
    metric_type: metricTypeInput.value,
    name: metricNameInput.value,
    unit_label: metricUnitLabelInput.value.trim() === "" ? null : metricUnitLabelInput.value,
  });

  if (!created) {
    return;
  }

  showSuccess("Metric created.", "Metrics");
  createDialogVisible.value = false;
  resetMetricForm();
  await goalsStore.loadGoals();
}

async function setMetricArchived(metricId: string, archived: boolean): Promise<void> {
  const updated = await metricsStore.setMetricArchived(metricId, archived);
  if (!updated) {
    return;
  }

  showSuccess(archived ? "Metric archived." : "Metric restored.", "Metrics");
  await goalsStore.loadGoals();
}

async function deleteMetricEntry(metricId: string): Promise<void> {
  const deleted = await metricsStore.deleteMetric(metricId);
  if (!deleted) {
    return;
  }

  showSuccess("Metric deleted.", "Metrics");
  await goalsStore.loadGoals();
}
</script>

<template>
  <div class="management-shell">
    <ManagementToolbar
      v-model:viewMode="viewMode"
      eyebrow="Metrics"
      title="Manage metrics"
      description="Reusable metric records are listed below. Add new ones from the toolbar and manage each row from the kebab menu."
      primary-action-label="Add metric"
      :primary-action-loading="metricsStore.submissionState === 'submitting'"
      @add="openCreateDialog"
    >
      <template #leading-actions>
        <label class="checkbox-row">
          <Checkbox
            v-model="metricsStore.includeArchived"
            binary
            input-id="include-archived-metrics"
            @change="metricsStore.loadMetrics()"
          />
          <span>Include archived</span>
        </label>
      </template>
    </ManagementToolbar>

    <div v-if="metricsStore.viewState === 'loading'" class="panel-card loading">
      <ProgressSpinner
        strokeWidth="5"
        style="width: 2rem; height: 2rem"
        animationDuration=".8s"
      />
      <span>Loading metrics.</span>
    </div>

    <div v-else-if="metricsStore.metrics.length === 0" class="panel-card empty-state">
      No metrics yet.
    </div>

    <div v-else-if="viewMode === 'table'" class="tracking-table-wrap panel-card">
      <table class="tracking-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Latest value</th>
            <th>Latest update</th>
            <th>Status</th>
            <th class="table-actions-column">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="metric in metricsStore.metrics" :key="metric.id">
            <td>
              <div class="table-primary-cell">
                <strong>{{ metric.name }}</strong>
                <span v-if="metric.unit_label !== null" class="table-secondary-text">
                  {{ metric.unit_label }}
                </span>
              </div>
            </td>
            <td>
              <Tag :value="metric.metric_type" severity="info" />
            </td>
            <td>{{ formatMetricLatestSummary(metric) }}</td>
            <td>
              {{ metric.latest_entry === null ? "No updates yet" : new Date(metric.latest_entry.recorded_at).toLocaleString() }}
            </td>
            <td>
              <Tag
                :value="metric.is_archived ? 'archived' : 'active'"
                :severity="metric.is_archived ? 'warning' : 'success'"
              />
            </td>
            <td class="table-kebab-cell">
              <Button
                icon="pi pi-ellipsis-v"
                text
                rounded
                aria-label="Metric actions"
                @click="toggleMetricRowMenu($event, metric.id)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="management-card-grid">
      <article
        v-for="metric in metricsStore.metrics"
        :key="metric.id"
        class="tracking-card"
      >
        <div class="tracking-card-header">
          <div>
            <h3>{{ metric.name }}</h3>
            <p>{{ formatMetricLatestSummary(metric) }}</p>
          </div>
          <div class="card-header-actions">
            <div class="metric-card-tags">
              <Tag :value="metric.metric_type" severity="info" />
              <Tag v-if="metric.is_archived" value="archived" severity="warning" />
            </div>
            <Button
              icon="pi pi-ellipsis-v"
              text
              rounded
              aria-label="Metric actions"
              @click="toggleMetricRowMenu($event, metric.id)"
            />
          </div>
        </div>
        <div class="goal-meta-grid">
          <div class="history-row">
            <strong>Latest update</strong>
            <span>
              {{
                metric.latest_entry === null
                  ? "No updates yet"
                  : new Date(metric.latest_entry.recorded_at).toLocaleString()
              }}
            </span>
          </div>
          <div class="history-row">
            <strong>Status</strong>
            <span>{{ metric.is_archived ? "Archived" : "Active" }}</span>
          </div>
        </div>
      </article>
    </div>

    <Menu ref="metricRowMenu" :model="metricRowMenuItems" popup />

    <Dialog
      v-model:visible="createDialogVisible"
      modal
      header="Add metric"
      class="profile-dialog"
      :style="{ width: 'min(34rem, 96vw)' }"
    >
      <div class="dialog-stack">
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Create a reusable metric</h3>
            <p>
              Metrics hold the values you update over time. Goals can reference them instead of
              owning isolated history.
            </p>
          </div>

          <div class="form-stack">
            <label class="field">
              <span class="label">Name</span>
              <InputText v-model="metricNameInput" />
            </label>

            <label class="field">
              <span class="label">Metric type</span>
              <select v-model="metricTypeInput" class="native-file-input">
                <option value="number">Number</option>
                <option value="date">Date</option>
              </select>
            </label>

            <label v-if="metricTypeInput === 'number'" class="field">
              <span class="label">Decimal places</span>
              <input
                v-model="metricDecimalPlacesInput"
                class="native-file-input"
                type="number"
                min="0"
                max="6"
                step="1"
              />
            </label>

            <label class="field">
              <span class="label">Unit label</span>
              <InputText v-model="metricUnitLabelInput" placeholder="Optional, like lbs" />
            </label>

            <label v-if="metricTypeInput === 'number'" class="field">
              <span class="label">Initial value</span>
              <input
                v-model="metricInitialNumberValueInput"
                class="native-file-input"
                type="number"
                :step="numberInputStep(parseDecimalPlaces(metricDecimalPlacesInput))"
              />
            </label>

            <label v-else class="field">
              <span class="label">Initial value</span>
              <input
                v-model="metricInitialDateValueInput"
                class="native-file-input"
                type="date"
              />
            </label>
          </div>

          <div class="dialog-actions-row">
            <Button
              label="Cancel"
              severity="secondary"
              text
              @click="createDialogVisible = false"
            />
            <Button
              label="Create metric"
              icon="pi pi-plus"
              :loading="metricsStore.submissionState === 'submitting'"
              @click="submitMetricForm"
            />
          </div>
        </section>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
@import "./management.css";

@media (max-width: 720px) {
  .checkbox-row {
    width: 100%;
  }
}
</style>
