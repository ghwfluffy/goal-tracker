<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import { numberInputStep, parseDecimalPlaces, parseOptionalNumber } from "../../lib/tracking";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";

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
const successMessage = ref("");

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

function resetMessages(): void {
  successMessage.value = "";
  metricsStore.errorMessage = "";
}

function resetMetricForm(): void {
  metricNameInput.value = "";
  metricTypeInput.value = "number";
  metricDecimalPlacesInput.value = "0";
  metricUnitLabelInput.value = "";
  metricInitialNumberValueInput.value = "";
  metricInitialDateValueInput.value = "";
}

function openCreateDialog(): void {
  resetMessages();
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
  resetMessages();
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

  successMessage.value = "Metric created.";
  createDialogVisible.value = false;
  resetMetricForm();
  await goalsStore.loadGoals();
}

async function setMetricArchived(metricId: string, archived: boolean): Promise<void> {
  resetMessages();
  const updated = await metricsStore.setMetricArchived(metricId, archived);
  if (!updated) {
    return;
  }

  successMessage.value = archived ? "Metric archived." : "Metric restored.";
  await goalsStore.loadGoals();
}

async function deleteMetricEntry(metricId: string): Promise<void> {
  resetMessages();
  const deleted = await metricsStore.deleteMetric(metricId);
  if (!deleted) {
    return;
  }

  successMessage.value = "Metric deleted.";
  await goalsStore.loadGoals();
}
</script>

<template>
  <div class="management-shell">
    <div class="management-toolbar panel-card">
      <div>
        <p class="panel-eyebrow">Metrics</p>
        <h2>Manage metrics</h2>
        <p>
          Reusable metric records are listed below. Add new ones from the toolbar and manage each
          row from the kebab menu.
        </p>
      </div>
      <div class="management-toolbar-actions">
        <label class="checkbox-row">
          <Checkbox
            v-model="metricsStore.includeArchived"
            binary
            input-id="include-archived-metrics"
            @change="metricsStore.loadMetrics()"
          />
          <span>Include archived</span>
        </label>
        <div class="view-toggle">
          <Button
            label="Table"
            icon="pi pi-table"
            :severity="viewMode === 'table' ? undefined : 'secondary'"
            :outlined="viewMode !== 'table'"
            @click="viewMode = 'table'"
          />
          <Button
            label="Cards"
            icon="pi pi-th-large"
            :severity="viewMode === 'cards' ? undefined : 'secondary'"
            :outlined="viewMode !== 'cards'"
            @click="viewMode = 'cards'"
          />
        </div>
        <Button
          label="Add metric"
          icon="pi pi-plus"
          :loading="metricsStore.submissionState === 'submitting'"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <Message v-if="successMessage !== ''" severity="success" :closable="false">
      {{ successMessage }}
    </Message>
    <Message v-if="metricsStore.errorMessage !== ''" severity="error" :closable="false">
      {{ metricsStore.errorMessage }}
    </Message>

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
        <Message v-if="successMessage !== ''" severity="success" :closable="false">
          {{ successMessage }}
        </Message>
        <Message v-if="metricsStore.errorMessage !== ''" severity="error" :closable="false">
          {{ metricsStore.errorMessage }}
        </Message>

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
.management-shell,
.management-card-grid,
.dialog-stack,
.dialog-section,
.form-stack,
.goal-meta-grid {
  display: grid;
  gap: 1rem;
}

.management-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.management-toolbar-actions,
.view-toggle,
.card-header-actions,
.dialog-actions-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.management-toolbar-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.management-card-grid {
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  align-items: start;
}

.loading,
.history-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tracking-table-wrap {
  overflow-x: auto;
}

.tracking-table {
  width: 100%;
  border-collapse: collapse;
}

.tracking-table th,
.tracking-table td {
  padding: 0.35rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid rgba(226, 232, 240, 0.75);
  vertical-align: middle;
}

.tracking-table th {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #64748b;
  background: rgba(248, 250, 252, 0.95);
}

.tracking-table td {
  font-size: 0.92rem;
  line-height: 1.2;
}

.table-primary-cell {
  display: grid;
  gap: 0.1rem;
}

.table-secondary-text {
  color: #64748b;
  font-size: 0.8rem;
}

.table-actions-column,
.table-kebab-cell {
  width: 1%;
  white-space: nowrap;
  text-align: right;
}

.tracking-table :deep(.p-tag) {
  padding: 0.2rem 0.45rem;
  font-size: 0.72rem;
  line-height: 1.1;
}

.tracking-table :deep(.p-button.p-button-icon-only) {
  width: 1.75rem;
  height: 1.75rem;
}

.tracking-table :deep(.p-button.p-button-text) {
  padding: 0.15rem;
}

.tracking-card {
  display: grid;
  gap: 1rem;
  padding: 1.1rem;
  border-radius: 1rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.84);
}

.tracking-card-header,
.history-row {
  justify-content: space-between;
}

.tracking-card-header h3,
.section-heading-text h3 {
  margin: 0;
}

.tracking-card-header p,
.section-heading-text p,
.management-toolbar p {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  color: #334155;
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  color: #0f172a;
}

.empty-state {
  color: #64748b;
}

.dialog-actions-row {
  justify-content: flex-end;
}

@media (max-width: 720px) {
  .management-toolbar,
  .tracking-card-header,
  .history-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .management-toolbar-actions,
  .view-toggle,
  .dialog-actions-row {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
