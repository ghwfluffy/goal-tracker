<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";
import InputText from "primevue/inputtext";

import type { DashboardSummary, DashboardWidgetSummary } from "../lib/api";
import { DEFAULT_PROFILE_TIMEZONE, formatDateOnly, formatTimestampInBrowserTimezone, getBrowserTimezone } from "../lib/time";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";
import { useMetricsStore } from "../stores/metrics";
import { useAuthStore } from "../stores/auth";
import DashboardWidgetChart from "./DashboardWidgetChart.vue";

const dashboardsStore = useDashboardsStore();
const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();
const authStore = useAuthStore();

const editMode = ref(false);
const selectedDashboardId = ref("");
const dashboardNameInput = ref("");
const dashboardDescriptionInput = ref("");
const dashboardMakeDefaultInput = ref(false);
const widgetTitleInput = ref("");
const widgetTypeInput = ref<"metric_history" | "metric_summary" | "goal_progress" | "goal_summary">(
  "metric_summary",
);
const widgetMetricIdInput = ref("");
const widgetGoalIdInput = ref("");
const widgetRollingWindowDaysInput = ref("30");
const dashboardSettingsNameInput = ref("");
const dashboardSettingsDescriptionInput = ref("");
const widgetEditTitles = ref<Record<string, string>>({});
const widgetEditWindowDays = ref<Record<string, string>>({});
const successMessage = ref("");

const browserTimezone = getBrowserTimezone();
const activeMetrics = computed(() => {
  return metricsStore.metrics.filter((metric) => !metric.is_archived);
});

const selectedDashboard = computed(() => {
  return dashboardsStore.dashboards.find((dashboard) => dashboard.id === selectedDashboardId.value) ?? null;
});

const dayBoundaryTimezone = computed(() => {
  return authStore.currentUser?.timezone ?? DEFAULT_PROFILE_TIMEZONE;
});

const widgetUsesMetric = computed(() => {
  return widgetTypeInput.value === "metric_history" || widgetTypeInput.value === "metric_summary";
});

const hasDashboards = computed(() => {
  return dashboardsStore.dashboards.length > 0;
});

function resetMessages(): void {
  successMessage.value = "";
  dashboardsStore.errorMessage = "";
}

function syncSelectedDashboard(): void {
  const availableIds = new Set(dashboardsStore.dashboards.map((dashboard) => dashboard.id));
  if (selectedDashboardId.value !== "" && availableIds.has(selectedDashboardId.value)) {
    return;
  }

  selectedDashboardId.value =
    dashboardsStore.dashboards.find((dashboard) => dashboard.is_default)?.id ??
    dashboardsStore.dashboards[0]?.id ??
    "";
}

function syncDashboardEditor(): void {
  dashboardSettingsNameInput.value = selectedDashboard.value?.name ?? "";
  dashboardSettingsDescriptionInput.value = selectedDashboard.value?.description ?? "";
}

function syncWidgetEditors(): void {
  widgetEditTitles.value = Object.fromEntries(
    (selectedDashboard.value?.widgets ?? []).map((widget) => [widget.id, widget.title]),
  );
  widgetEditWindowDays.value = Object.fromEntries(
    (selectedDashboard.value?.widgets ?? []).map((widget) => [
      widget.id,
      widget.rolling_window_days === null ? "" : String(widget.rolling_window_days),
    ]),
  );
}

function resetDashboardCreateForm(): void {
  dashboardNameInput.value = "";
  dashboardDescriptionInput.value = "";
  dashboardMakeDefaultInput.value = false;
}

function resetWidgetCreateForm(): void {
  widgetTitleInput.value = "";
  widgetTypeInput.value = "metric_summary";
  widgetMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
  widgetGoalIdInput.value = goalsStore.goals[0]?.id ?? "";
  widgetRollingWindowDaysInput.value = "30";
}

function parseRollingWindow(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatMetricValue(widget: DashboardWidgetSummary): string {
  const metric = widget.metric ?? widget.goal?.metric ?? null;
  const latestEntry = metric?.latest_entry ?? null;
  if (metric === null || latestEntry === null) {
    return "No value yet";
  }

  if (metric.metric_type === "number") {
    const value = latestEntry.number_value;
    return value === null
      ? "No value yet"
      : `${value.toFixed(metric.decimal_places ?? 0)}${metric.unit_label ? ` ${metric.unit_label}` : ""}`;
  }

  return formatDateOnly(latestEntry.date_value);
}

function goalProgressLabel(widget: DashboardWidgetSummary): string {
  if (widget.current_progress_percent === null) {
    return "Progress needs a target value and enough history.";
  }

  return `${Math.round(widget.current_progress_percent)}% complete`;
}

async function createDashboardEntry(): Promise<void> {
  resetMessages();
  const created = await dashboardsStore.createDashboard({
    description: dashboardDescriptionInput.value.trim() === "" ? null : dashboardDescriptionInput.value,
    make_default: dashboardMakeDefaultInput.value,
    name: dashboardNameInput.value,
  });

  if (!created) {
    return;
  }

  successMessage.value = "Dashboard created.";
  resetDashboardCreateForm();
  syncSelectedDashboard();
}

function enterEditMode(): void {
  resetMessages();
  editMode.value = true;
  syncDashboardEditor();
  syncWidgetEditors();
}

function exitEditMode(): void {
  editMode.value = false;
  syncDashboardEditor();
  syncWidgetEditors();
}

async function saveDashboardSettings(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const updated = await dashboardsStore.updateDashboard(selectedDashboard.value.id, {
    description:
      dashboardSettingsDescriptionInput.value.trim() === ""
        ? null
        : dashboardSettingsDescriptionInput.value,
    name: dashboardSettingsNameInput.value,
  });

  if (updated) {
    successMessage.value = "Dashboard updated.";
  }
}

async function makeDashboardDefault(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const updated = await dashboardsStore.updateDashboard(selectedDashboard.value.id, {
    make_default: true,
  });

  if (updated) {
    successMessage.value = "Default dashboard updated.";
    syncSelectedDashboard();
  }
}

async function removeDashboard(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const deleted = await dashboardsStore.deleteDashboard(selectedDashboard.value.id);
  if (deleted) {
    successMessage.value = "Dashboard deleted.";
    syncSelectedDashboard();
    syncDashboardEditor();
    syncWidgetEditors();
  }
}

async function addWidget(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const created = await dashboardsStore.createWidget(selectedDashboard.value.id, {
    goal_id: widgetUsesMetric.value ? null : widgetGoalIdInput.value || null,
    metric_id: widgetUsesMetric.value ? widgetMetricIdInput.value || null : null,
    rolling_window_days: parseRollingWindow(widgetRollingWindowDaysInput.value),
    title: widgetTitleInput.value,
    widget_type: widgetTypeInput.value,
  });

  if (created) {
    successMessage.value = "Widget added.";
    resetWidgetCreateForm();
    syncWidgetEditors();
  }
}

async function saveWidget(widgetId: string): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetId, {
    rolling_window_days: parseRollingWindow(widgetEditWindowDays.value[widgetId] ?? ""),
    title: widgetEditTitles.value[widgetId] ?? "",
  });

  if (updated) {
    successMessage.value = "Widget updated.";
  }
}

async function removeWidget(widgetId: string): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  const deleted = await dashboardsStore.deleteWidget(selectedDashboard.value.id, widgetId);
  if (deleted) {
    successMessage.value = "Widget removed.";
    syncWidgetEditors();
  }
}

watch(
  () => dashboardsStore.dashboards,
  () => {
    syncSelectedDashboard();
    syncDashboardEditor();
    syncWidgetEditors();
  },
  { deep: true, immediate: true },
);

watch(
  () => widgetTypeInput.value,
  () => {
    if (widgetUsesMetric.value && widgetMetricIdInput.value === "") {
      widgetMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }

    if (!widgetUsesMetric.value && widgetGoalIdInput.value === "") {
      widgetGoalIdInput.value = goalsStore.goals[0]?.id ?? "";
    }
  },
  { immediate: true },
);

watch(
  () => metricsStore.metrics,
  () => {
    const activeMetricIds = new Set(activeMetrics.value.map((metric) => metric.id));
    if (widgetMetricIdInput.value === "" || !activeMetricIds.has(widgetMetricIdInput.value)) {
      widgetMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

watch(
  () => goalsStore.goals,
  () => {
    if (widgetGoalIdInput.value === "") {
      widgetGoalIdInput.value = goalsStore.goals[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);
</script>

<template>
  <div class="dashboard-shell">
    <div class="dashboard-sidebar panel-card">
      <p class="panel-eyebrow">Dashboards</p>
      <h2>Your saved views</h2>
      <p class="sidebar-copy">
        Times render in your browser timezone, while day boundaries use your profile timezone.
      </p>

      <div class="timezone-meta">
        <div class="timezone-row">
          <span class="label">Browser timezone</span>
          <strong>{{ browserTimezone }}</strong>
        </div>
        <div class="timezone-row">
          <span class="label">Day boundary timezone</span>
          <strong>{{ dayBoundaryTimezone }}</strong>
        </div>
      </div>

      <div v-if="dashboardsStore.viewState === 'loading'" class="loading">
        <ProgressSpinner strokeWidth="5" style="width: 2rem; height: 2rem" animationDuration=".8s" />
        <span>Loading dashboards.</span>
      </div>

      <div v-else-if="hasDashboards" class="dashboard-list">
        <button
          v-for="dashboard in dashboardsStore.dashboards"
          :key="dashboard.id"
          class="dashboard-list-item"
          :class="{ active: dashboard.id === selectedDashboardId }"
          type="button"
          @click="selectedDashboardId = dashboard.id"
        >
          <span>{{ dashboard.name }}</span>
          <Tag v-if="dashboard.is_default" value="Default" severity="success" />
        </button>
      </div>

      <div v-else class="empty-state">Create your first dashboard to start arranging widgets.</div>

      <div class="form-stack">
        <label class="field">
          <span class="label">New dashboard</span>
          <InputText v-model="dashboardNameInput" placeholder="Morning check-in" />
        </label>

        <label class="field">
          <span class="label">Description</span>
          <textarea
            v-model="dashboardDescriptionInput"
            class="native-textarea"
            rows="3"
            placeholder="Optional summary for this dashboard"
          />
        </label>

        <label class="checkbox-row">
          <input v-model="dashboardMakeDefaultInput" type="checkbox" />
          <span>Make this the default dashboard</span>
        </label>

        <Button
          label="Create dashboard"
          icon="pi pi-plus"
          :loading="dashboardsStore.submissionState === 'submitting'"
          @click="createDashboardEntry"
        />
      </div>
    </div>

    <div class="dashboard-main">
      <Message v-if="successMessage !== ''" severity="success" :closable="false">
        {{ successMessage }}
      </Message>
      <Message v-if="dashboardsStore.errorMessage !== ''" severity="error" :closable="false">
        {{ dashboardsStore.errorMessage }}
      </Message>

      <div v-if="selectedDashboard !== null" class="dashboard-content">
        <div class="dashboard-header panel-card">
          <div>
            <p class="panel-eyebrow">Selected dashboard</p>
            <div class="dashboard-title-row">
              <h2>{{ selectedDashboard.name }}</h2>
              <Tag v-if="selectedDashboard.is_default" value="Default" severity="success" />
            </div>
            <p v-if="selectedDashboard.description !== null" class="dashboard-description">
              {{ selectedDashboard.description }}
            </p>
          </div>

          <div class="dashboard-actions">
            <Button
              v-if="!selectedDashboard.is_default"
              label="Make default"
              icon="pi pi-star"
              severity="secondary"
              @click="makeDashboardDefault"
            />
            <Button
              :label="editMode ? 'Exit edit mode' : 'Edit dashboard'"
              :icon="editMode ? 'pi pi-check' : 'pi pi-pencil'"
              @click="editMode ? exitEditMode() : enterEditMode()"
            />
          </div>
        </div>

        <div v-if="editMode" class="dashboard-editor">
          <div class="panel-card">
            <p class="panel-eyebrow">Dashboard settings</p>
            <h3>Edit dashboard details</h3>
            <div class="form-stack">
              <label class="field">
                <span class="label">Name</span>
                <InputText v-model="dashboardSettingsNameInput" />
              </label>
              <label class="field">
                <span class="label">Description</span>
                <textarea v-model="dashboardSettingsDescriptionInput" class="native-textarea" rows="3" />
              </label>
              <div class="editor-actions">
                <Button
                  label="Save dashboard"
                  icon="pi pi-save"
                  :loading="dashboardsStore.submissionState === 'submitting'"
                  @click="saveDashboardSettings"
                />
                <Button
                  label="Delete dashboard"
                  icon="pi pi-trash"
                  severity="danger"
                  outlined
                  :loading="dashboardsStore.submissionState === 'submitting'"
                  @click="removeDashboard"
                />
              </div>
            </div>
          </div>

          <div class="panel-card">
            <p class="panel-eyebrow">Add widget</p>
            <h3>Compose the dashboard</h3>
            <div class="form-stack">
              <label class="field">
                <span class="label">Widget title</span>
                <InputText v-model="widgetTitleInput" placeholder="Weight trend" />
              </label>

              <label class="field">
                <span class="label">Widget type</span>
                <select v-model="widgetTypeInput" class="native-file-input">
                  <option value="metric_summary">Metric summary</option>
                  <option value="metric_history">Metric history</option>
                  <option value="goal_summary">Goal summary</option>
                  <option value="goal_progress">Goal progress</option>
                </select>
              </label>

              <label v-if="widgetUsesMetric" class="field">
                <span class="label">Metric</span>
                <select v-model="widgetMetricIdInput" class="native-file-input">
                  <option v-for="metric in activeMetrics" :key="metric.id" :value="metric.id">
                    {{ metric.name }} ({{ metric.metric_type }})
                  </option>
                </select>
              </label>

              <label v-else class="field">
                <span class="label">Goal</span>
                <select v-model="widgetGoalIdInput" class="native-file-input">
                  <option v-for="goal in goalsStore.goals" :key="goal.id" :value="goal.id">
                    {{ goal.title }}
                  </option>
                </select>
              </label>

              <label class="field">
                <span class="label">Rolling window days</span>
                <input
                  v-model="widgetRollingWindowDaysInput"
                  class="native-file-input"
                  type="number"
                  min="1"
                  step="1"
                />
              </label>

              <Button
                label="Add widget"
                icon="pi pi-plus-circle"
                :loading="dashboardsStore.submissionState === 'submitting'"
                @click="addWidget"
              />
            </div>
          </div>

          <div class="panel-card">
            <p class="panel-eyebrow">Current widgets</p>
            <h3>Adjust saved widgets</h3>

            <div v-if="selectedDashboard.widgets.length === 0" class="empty-state">
              No widgets on this dashboard yet.
            </div>

            <div v-else class="widget-edit-list">
              <article v-for="widget in selectedDashboard.widgets" :key="widget.id" class="widget-edit-card">
                <label class="field">
                  <span class="label">Title</span>
                  <InputText v-model="widgetEditTitles[widget.id]" />
                </label>
                <label class="field">
                  <span class="label">Rolling window days</span>
                  <input
                    v-model="widgetEditWindowDays[widget.id]"
                    class="native-file-input"
                    type="number"
                    min="1"
                    step="1"
                  />
                </label>
                <div class="editor-actions">
                  <Button
                    label="Save"
                    icon="pi pi-save"
                    severity="secondary"
                    :loading="dashboardsStore.submissionState === 'submitting'"
                    @click="saveWidget(widget.id)"
                  />
                  <Button
                    label="Delete"
                    icon="pi pi-trash"
                    severity="danger"
                    outlined
                    :loading="dashboardsStore.submissionState === 'submitting'"
                    @click="removeWidget(widget.id)"
                  />
                </div>
              </article>
            </div>
          </div>
        </div>

        <div v-else-if="selectedDashboard.widgets.length === 0" class="panel-card empty-panel">
          <p class="panel-eyebrow">No widgets yet</p>
          <h3>Switch to edit mode to build this dashboard.</h3>
        </div>

        <div v-else class="widget-grid">
          <article v-for="widget in selectedDashboard.widgets" :key="widget.id" class="panel-card widget-card">
            <div class="widget-card-header">
              <div>
                <p class="panel-eyebrow">{{ widget.widget_type.replaceAll("_", " ") }}</p>
                <h3>{{ widget.title }}</h3>
              </div>
              <Tag :value="widget.target_met ? 'On target' : 'Tracking'" :severity="widget.target_met ? 'success' : 'info'" />
            </div>

            <p v-if="widget.metric !== null" class="widget-summary">
              Latest value: <strong>{{ formatMetricValue(widget) }}</strong>
            </p>
            <p v-else class="widget-summary">
              {{ goalProgressLabel(widget) }}
            </p>

            <p v-if="widget.goal !== null" class="widget-meta">
              Goal window: {{ widget.goal.start_date }}<span v-if="widget.goal.target_date !== null"> to {{ widget.goal.target_date }}</span>
            </p>
            <p
              v-else-if="widget.metric?.latest_entry !== null"
              class="widget-meta"
            >
              Last update: {{ formatTimestampInBrowserTimezone(widget.metric.latest_entry.recorded_at) }}
            </p>

            <DashboardWidgetChart :widget="widget" />
          </article>
        </div>
      </div>

      <div v-else class="panel-card empty-panel">
        <p class="panel-eyebrow">Dashboards</p>
        <h2>No dashboard selected</h2>
        <p>Create a dashboard in the left panel to start arranging widgets.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: grid;
  grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr);
  gap: 1.5rem;
}

.dashboard-main {
  display: grid;
  gap: 1rem;
}

.dashboard-sidebar,
.dashboard-header,
.widget-card,
.empty-panel {
  background: rgba(255, 255, 255, 0.92);
}

.sidebar-copy,
.dashboard-description,
.widget-summary,
.widget-meta {
  color: #475569;
}

.timezone-meta,
.dashboard-list,
.form-stack,
.widget-edit-list,
.dashboard-editor {
  display: grid;
  gap: 1rem;
}

.timezone-row,
.widget-card-header,
.dashboard-title-row,
.dashboard-actions,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.dashboard-list-item {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: #fff;
  border-radius: 1rem;
  padding: 0.9rem 1rem;
  text-align: left;
  cursor: pointer;
}

.dashboard-list-item.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.dashboard-content,
.widget-grid {
  display: grid;
  gap: 1rem;
}

.dashboard-editor {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.widget-grid {
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
}

.widget-edit-card {
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 1rem;
  padding: 1rem;
  display: grid;
  gap: 0.9rem;
}

.widget-card {
  display: grid;
  gap: 0.75rem;
}

@media (max-width: 960px) {
  .dashboard-shell,
  .dashboard-editor {
    grid-template-columns: 1fr;
  }

  .dashboard-actions,
  .editor-actions {
    flex-wrap: wrap;
  }
}
</style>
