<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Button from "primevue/button";
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
const metricDialogVisible = ref(false);
const metricDialogMode = ref<"create" | "edit">("create");
const metricEditId = ref("");
const metricImportDialogVisible = ref(false);
const metricImportMetricId = ref("");
const metricImportTextInput = ref("");
const viewMode = ref<"table" | "cards">("table");

const metricNameInput = ref("");
const metricTypeInput = ref<"number" | "date">("number");
const metricUpdateTypeInput = ref<"success" | "failure">("success");
const metricDecimalPlacesInput = ref("0");
const metricUnitLabelInput = ref("");
const metricInitialNumberValueInput = ref("");
const metricInitialDateValueInput = ref("");
const metricReminderTime1Input = ref("06:00");
const metricReminderTime2Input = ref("");
const { showSuccess } = useAppToast();

const selectedMetricMenuMetric = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === activeMetricMenuId.value) ?? null;
});

const editingMetric = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === metricEditId.value) ?? null;
});

const importingMetric = computed(() => {
  return metricsStore.metrics.find((metric) => metric.id === metricImportMetricId.value) ?? null;
});

const metricRowMenuItems = computed<MenuItem[]>(() => {
  const metric = selectedMetricMenuMetric.value;
  if (metric === null) {
    return [];
  }

  const items: MenuItem[] = [];

  items.push({
    icon: "pi pi-pencil",
    label: "Edit",
    command: () => openEditDialog(metric),
  });

  if (!metric.is_archived) {
    items.push({
      icon: "pi pi-plus-circle",
      label: "Add update",
      command: () => emit("openMetricEntry", metric.id),
    });
    items.push({
      icon: "pi pi-upload",
      label: "Import values",
      command: () => openImportDialog(metric),
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
  metricUpdateTypeInput.value = "success";
  metricDecimalPlacesInput.value = "0";
  metricUnitLabelInput.value = "";
  metricInitialNumberValueInput.value = "";
  metricInitialDateValueInput.value = "";
  metricReminderTime1Input.value = "06:00";
  metricReminderTime2Input.value = "";
}

function openCreateDialog(): void {
  metricDialogMode.value = "create";
  metricEditId.value = "";
  resetMetricForm();
  metricDialogVisible.value = true;
}

function openEditDialog(metric: (typeof metricsStore.metrics)[number]): void {
  metricDialogMode.value = "edit";
  metricEditId.value = metric.id;
  metricNameInput.value = metric.name;
  metricTypeInput.value = metric.metric_type;
  metricUpdateTypeInput.value = metric.update_type;
  metricDecimalPlacesInput.value = String(metric.decimal_places ?? 0);
  metricUnitLabelInput.value = metric.unit_label ?? "";
  metricInitialNumberValueInput.value = "";
  metricInitialDateValueInput.value = "";
  metricReminderTime1Input.value = metric.reminder_time_1;
  metricReminderTime2Input.value = metric.reminder_time_2 ?? "";
  metricDialogVisible.value = true;
}

function openImportDialog(metric: (typeof metricsStore.metrics)[number]): void {
  metricImportMetricId.value = metric.id;
  metricImportTextInput.value = "";
  metricImportDialogVisible.value = true;
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
  if (metricDialogMode.value === "create") {
    const created = await metricsStore.createMetric({
      decimal_places:
        metricTypeInput.value === "number" ? parseDecimalPlaces(metricDecimalPlacesInput.value) : null,
      initial_date_value:
        metricTypeInput.value === "date" ? metricInitialDateValueInput.value || null : null,
      initial_number_value:
        metricTypeInput.value === "number" ? parseOptionalNumber(metricInitialNumberValueInput.value) : null,
      metric_type: metricTypeInput.value,
      name: metricNameInput.value,
      reminder_time_1: metricReminderTime1Input.value || null,
      reminder_time_2: metricReminderTime2Input.value || null,
      update_type: metricTypeInput.value === "date" ? metricUpdateTypeInput.value : null,
      unit_label: metricUnitLabelInput.value.trim() === "" ? null : metricUnitLabelInput.value,
    });

    if (!created) {
      return;
    }

    showSuccess("Metric created.", "Metrics");
    metricDialogVisible.value = false;
    resetMetricForm();
    await goalsStore.loadGoals();
    return;
  }

  if (editingMetric.value === null) {
    return;
  }

  const updated = await metricsStore.updateMetricDetails(editingMetric.value.id, {
    decimal_places:
      metricTypeInput.value === "number" ? parseDecimalPlaces(metricDecimalPlacesInput.value) : null,
    name: metricNameInput.value,
    reminder_time_1: metricReminderTime1Input.value || null,
    reminder_time_2: metricReminderTime2Input.value || null,
    update_type: metricTypeInput.value === "date" ? metricUpdateTypeInput.value : null,
    unit_label: metricUnitLabelInput.value.trim() === "" ? null : metricUnitLabelInput.value,
  });
  if (!updated) {
    return;
  }

  showSuccess("Metric updated.", "Metrics");
  metricDialogVisible.value = false;
}

function formatImportSuccessMessage(importedCount: number, skippedCount: number): string {
  if (skippedCount === 0) {
    return `Imported ${importedCount} value${importedCount === 1 ? "" : "s"}.`;
  }

  return `Imported ${importedCount} value${importedCount === 1 ? "" : "s"} and skipped ${skippedCount} duplicate${skippedCount === 1 ? "" : "s"}.`;
}

async function submitImportForm(): Promise<void> {
  if (importingMetric.value === null) {
    return;
  }

  const result = await metricsStore.importMetricEntries(importingMetric.value.id, {
    data: metricImportTextInput.value,
  });
  if (result === null) {
    return;
  }

  showSuccess(
    formatImportSuccessMessage(result.importedCount, result.skippedCount),
    "Metrics",
  );
  metricImportDialogVisible.value = false;
  metricImportTextInput.value = "";
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

function toggleIncludeArchived(): void {
  metricsStore.includeArchived = !metricsStore.includeArchived;
  void metricsStore.loadMetrics();
}
</script>

<template>
  <div class="management-shell">
    <ManagementToolbar
      v-model:viewMode="viewMode"
      title="Manage metrics"
      description="Reusable metric records are listed below. Add new ones from the toolbar and manage each row from the kebab menu."
      primary-action-label="Add metric"
      :primary-action-loading="metricsStore.submissionState === 'submitting'"
      @add="openCreateDialog"
    >
      <template #leading-actions>
        <Button
          label="Archived"
          icon="pi pi-box"
          severity="secondary"
          :outlined="!metricsStore.includeArchived"
          class="toolbar-filter-button"
          aria-label="Toggle archived metrics"
          @click="toggleIncludeArchived"
        />
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
            <th>Latest value</th>
            <th class="mobile-hide-column">Type</th>
            <th class="mobile-hide-column">Latest update</th>
            <th class="mobile-hide-column">Status</th>
            <th class="table-actions-column">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="metric in metricsStore.metrics" :key="metric.id">
            <td>
              <div class="table-primary-cell">
                <strong>{{ metric.name }}</strong>
              </div>
            </td>
            <td>
              {{ formatMetricLatestSummary(metric) }}
            </td>
            <td class="mobile-hide-column">
              <Tag :value="metric.metric_type" severity="info" />
            </td>
            <td class="mobile-hide-column">
              {{ metric.latest_entry === null ? "No updates yet" : new Date(metric.latest_entry.recorded_at).toLocaleString() }}
            </td>
            <td class="mobile-hide-column">
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
          <div class="history-row">
            <strong>Reminders</strong>
            <span>
              {{ metric.reminder_time_1 }}<template v-if="metric.reminder_time_2 !== null">, {{ metric.reminder_time_2 }}</template>
            </span>
          </div>
          <div v-if="metric.metric_type === 'date'" class="history-row">
            <strong>Update type</strong>
            <span>{{ metric.update_type === "failure" ? "Failure" : "Success" }}</span>
          </div>
        </div>
      </article>
    </div>

    <Menu ref="metricRowMenu" :model="metricRowMenuItems" popup />

    <Dialog
      v-model:visible="metricDialogVisible"
      modal
      :header="metricDialogMode === 'create' ? 'Add metric' : 'Edit metric'"
      class="profile-dialog"
      :style="{ width: 'min(34rem, 96vw)' }"
    >
      <div class="dialog-stack">
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>{{ metricDialogMode === "create" ? "Create a reusable metric" : "Edit metric" }}</h3>
            <p v-if="metricDialogMode === 'create'">
              Metrics hold the values you update over time. Goals can reference them instead of
              owning isolated history.
            </p>
            <p v-else>Update the metric details and reminder schedule.</p>
          </div>

          <div class="form-stack">
            <label class="field">
              <span class="label">Name</span>
              <InputText v-model="metricNameInput" />
            </label>

            <template v-if="metricDialogMode === 'create'">
              <label class="field">
                <span class="label">Metric type</span>
                <select v-model="metricTypeInput" class="native-file-input">
                  <option value="number">Number</option>
                  <option value="date">Date</option>
                </select>
              </label>
            </template>
            <div v-else class="widget-dialog-note">
              Type: {{ metricTypeInput }}
            </div>

            <label v-if="metricTypeInput === 'date'" class="field">
              <span class="label">Update type</span>
              <select v-model="metricUpdateTypeInput" class="native-file-input">
                <option value="success">Success</option>
                <option value="failure">Failure</option>
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

            <div class="metric-reminder-grid">
              <label class="field">
                <span class="label">First reminder</span>
                <input v-model="metricReminderTime1Input" class="native-file-input" type="time" />
              </label>

              <label class="field">
                <span class="label">Second reminder</span>
                <input v-model="metricReminderTime2Input" class="native-file-input" type="time" />
              </label>
            </div>

            <label v-if="metricDialogMode === 'create' && metricTypeInput === 'number'" class="field">
              <span class="label">Initial value</span>
              <input
                v-model="metricInitialNumberValueInput"
                class="native-file-input"
                type="number"
                :step="numberInputStep(parseDecimalPlaces(metricDecimalPlacesInput))"
              />
            </label>

            <label v-else-if="metricDialogMode === 'create'" class="field">
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
              @click="metricDialogVisible = false"
            />
            <Button
              :label="metricDialogMode === 'create' ? 'Create metric' : 'Save metric'"
              :icon="metricDialogMode === 'create' ? 'pi pi-plus' : 'pi pi-save'"
              :loading="metricsStore.submissionState === 'submitting'"
              @click="submitMetricForm"
            />
          </div>
        </section>
      </div>
    </Dialog>

    <Dialog
      v-model:visible="metricImportDialogVisible"
      modal
      header="Import metric values"
      class="profile-dialog"
      :style="{ width: 'min(42rem, 96vw)' }"
    >
      <div class="dialog-stack">
        <section v-if="importingMetric !== null" class="dialog-section">
          <div class="section-heading-text">
            <h3>Import values into {{ importingMetric.name }}</h3>
            <p>
              Paste one line per entry as timestamp plus value. Tabs and commas are both accepted.
              Header rows are optional.
            </p>
          </div>

          <label class="field">
            <span class="label">Paste data</span>
            <textarea
              v-model="metricImportTextInput"
              class="native-file-input metric-import-textarea"
              rows="10"
              spellcheck="false"
              placeholder="2026-01-05 20:56\t298.6&#10;2026-01-06 07:00\t296.6"
            />
          </label>

          <div class="widget-dialog-note">
            Use local-style timestamps like <code>2026-01-05 20:56</code> or ISO timestamps like
            <code>2026-01-05T20:56:00Z</code>. Importing the same rows again skips duplicates.
          </div>

          <div class="dialog-actions-row">
            <Button
              label="Cancel"
              severity="secondary"
              text
              @click="metricImportDialogVisible = false"
            />
            <Button
              label="Import values"
              icon="pi pi-upload"
              :loading="metricsStore.submissionState === 'submitting'"
              @click="submitImportForm"
            />
          </div>
        </section>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
@import "./management.css";

.metric-reminder-grid {
  display: grid;
  gap: 1rem;
}

.metric-import-textarea {
  min-height: 16rem;
  resize: vertical;
  font-family: "SFMono-Regular", "Consolas", "Liberation Mono", monospace;
}

@media (max-width: 720px) {
  .toolbar-filter-button :deep(.p-button-label) {
    display: none;
  }
}
</style>
