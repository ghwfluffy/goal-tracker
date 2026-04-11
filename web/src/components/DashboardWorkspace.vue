<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Dropdown from "primevue/dropdown";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import type { DashboardWidgetSummary } from "../lib/api";
import { formatDateOnly, formatTimestampInBrowserTimezone } from "../lib/time";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";
import { useMetricsStore } from "../stores/metrics";
import DashboardWidgetChart from "./DashboardWidgetChart.vue";

type WidgetType = DashboardWidgetSummary["widget_type"];

interface WidgetLayoutDraft {
  grid_h: number;
  grid_w: number;
  grid_x: number;
  grid_y: number;
}

interface WidgetInteractionState {
  kind: "drag" | "resize";
  start_client_x: number;
  start_client_y: number;
  start_layout: WidgetLayoutDraft;
  widget_id: string;
}

const GRID_COLUMNS = 12;
const GRID_ROW_HEIGHT_PX = 96;
const MAX_WIDGET_HEIGHT = 12;

const dashboardsStore = useDashboardsStore();
const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();

const selectedDashboardId = ref("");
const editMode = ref(false);
const successMessage = ref("");

const dashboardDialogVisible = ref(false);
const dashboardDialogMode = ref<"create" | "edit">("create");
const dashboardNameInput = ref("");
const dashboardDescriptionInput = ref("");

const widgetDialogVisible = ref(false);
const widgetDialogMode = ref<"create" | "edit">("create");
const widgetEditId = ref("");
const widgetTitleInput = ref("");
const widgetTypeInput = ref<WidgetType>("metric_summary");
const widgetMetricIdInput = ref("");
const widgetGoalIdInput = ref("");
const widgetRollingWindowDaysInput = ref("30");

const gridHost = ref<HTMLElement | null>(null);
const gridWidth = ref(0);
const localLayouts = ref<Record<string, WidgetLayoutDraft>>({});
const activeInteraction = ref<WidgetInteractionState | null>(null);
let resizeObserver: ResizeObserver | null = null;

const dashboardOptions = computed(() => {
  return dashboardsStore.dashboards.map((dashboard) => ({
    label: dashboard.is_default ? `${dashboard.name} (Default)` : dashboard.name,
    value: dashboard.id,
  }));
});

const selectedDashboard = computed(() => {
  return dashboardsStore.dashboards.find((dashboard) => dashboard.id === selectedDashboardId.value) ?? null;
});

const orderedWidgets = computed(() => {
  const widgets = selectedDashboard.value?.widgets ?? [];
  return [...widgets].sort((left, right) => {
    const leftLayout = getWidgetLayout(left);
    const rightLayout = getWidgetLayout(right);
    if (leftLayout.grid_y !== rightLayout.grid_y) {
      return leftLayout.grid_y - rightLayout.grid_y;
    }
    if (leftLayout.grid_x !== rightLayout.grid_x) {
      return leftLayout.grid_x - rightLayout.grid_x;
    }
    return left.display_order - right.display_order;
  });
});

const activeMetrics = computed(() => {
  return metricsStore.metrics.filter((metric) => !metric.is_archived);
});

const widgetTypeOptions = [
  { label: "Metric summary", value: "metric_summary" },
  { label: "Metric history", value: "metric_history" },
  { label: "Goal summary", value: "goal_summary" },
  { label: "Goal progress", value: "goal_progress" },
] satisfies Array<{ label: string; value: WidgetType }>;

const widgetUsesMetric = computed(() => {
  return widgetTypeInput.value === "metric_history" || widgetTypeInput.value === "metric_summary";
});

const columnWidth = computed(() => {
  if (gridWidth.value <= 0) {
    return 0;
  }
  return gridWidth.value / GRID_COLUMNS;
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

function snapshotWidgetLayouts(): void {
  localLayouts.value = Object.fromEntries(
    (selectedDashboard.value?.widgets ?? []).map((widget) => [
      widget.id,
      {
        grid_h: widget.grid_h,
        grid_w: widget.grid_w,
        grid_x: widget.grid_x,
        grid_y: widget.grid_y,
      },
    ]),
  );
}

function refreshGridMetrics(): void {
  gridWidth.value = gridHost.value?.clientWidth ?? 0;
}

function getWidgetLayout(widget: DashboardWidgetSummary): WidgetLayoutDraft {
  return (
    localLayouts.value[widget.id] ?? {
      grid_h: widget.grid_h,
      grid_w: widget.grid_w,
      grid_x: widget.grid_x,
      grid_y: widget.grid_y,
    }
  );
}

function widgetGridStyle(widget: DashboardWidgetSummary): Record<string, string> {
  const layout = getWidgetLayout(widget);
  return {
    gridColumn: `${layout.grid_x + 1} / span ${layout.grid_w}`,
    gridRow: `${layout.grid_y + 1} / span ${layout.grid_h}`,
  };
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized === "" ? null : normalized;
}

function parseRollingWindow(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatWidgetType(widgetType: WidgetType): string {
  return widgetType.replaceAll("_", " ");
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

function widgetSubjectLabel(widget: DashboardWidgetSummary): string {
  if (widget.metric !== null) {
    return widget.metric.name;
  }
  return widget.goal?.title ?? "Goal";
}

function openCreateDashboardDialog(): void {
  resetMessages();
  dashboardDialogMode.value = "create";
  dashboardNameInput.value = "";
  dashboardDescriptionInput.value = "";
  dashboardDialogVisible.value = true;
}

function openEditDashboardDialog(): void {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  dashboardDialogMode.value = "edit";
  dashboardNameInput.value = selectedDashboard.value.name;
  dashboardDescriptionInput.value = selectedDashboard.value.description ?? "";
  dashboardDialogVisible.value = true;
}

async function submitDashboardDialog(): Promise<void> {
  if (dashboardDialogMode.value === "create") {
    const createdDashboardId = await dashboardsStore.createDashboard({
      description: normalizeOptionalText(dashboardDescriptionInput.value),
      make_default: false,
      name: dashboardNameInput.value,
    });
    if (createdDashboardId !== null) {
      selectedDashboardId.value = createdDashboardId;
      dashboardDialogVisible.value = false;
      successMessage.value = "Dashboard created.";
    }
    return;
  }

  if (selectedDashboard.value === null) {
    return;
  }

  const updated = await dashboardsStore.updateDashboard(selectedDashboard.value.id, {
    description: normalizeOptionalText(dashboardDescriptionInput.value),
    name: dashboardNameInput.value,
  });
  if (updated) {
    dashboardDialogVisible.value = false;
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
  }
}

async function removeDashboard(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }
  if (!window.confirm(`Delete dashboard "${selectedDashboard.value.name}"?`)) {
    return;
  }

  resetMessages();
  const deleted = await dashboardsStore.deleteDashboard(selectedDashboard.value.id);
  if (deleted) {
    editMode.value = false;
    successMessage.value = "Dashboard deleted.";
  }
}

function enterEditMode(): void {
  if (selectedDashboard.value === null) {
    return;
  }
  resetMessages();
  snapshotWidgetLayouts();
  editMode.value = true;
}

function exitEditMode(): void {
  editMode.value = false;
  stopInteraction();
  snapshotWidgetLayouts();
}

function openCreateWidgetDialog(): void {
  resetMessages();
  widgetDialogMode.value = "create";
  widgetEditId.value = "";
  widgetTitleInput.value = "";
  widgetTypeInput.value = "metric_summary";
  widgetMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
  widgetGoalIdInput.value = goalsStore.goals[0]?.id ?? "";
  widgetRollingWindowDaysInput.value = "30";
  widgetDialogVisible.value = true;
}

function openEditWidgetDialog(widget: DashboardWidgetSummary): void {
  resetMessages();
  widgetDialogMode.value = "edit";
  widgetEditId.value = widget.id;
  widgetTitleInput.value = widget.title;
  widgetTypeInput.value = widget.widget_type;
  widgetMetricIdInput.value = widget.metric?.id ?? "";
  widgetGoalIdInput.value = widget.goal?.id ?? "";
  widgetRollingWindowDaysInput.value =
    widget.rolling_window_days === null ? "" : String(widget.rolling_window_days);
  widgetDialogVisible.value = true;
}

async function submitWidgetDialog(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  resetMessages();
  if (widgetDialogMode.value === "create") {
    const created = await dashboardsStore.createWidget(selectedDashboard.value.id, {
      goal_id: widgetUsesMetric.value ? null : widgetGoalIdInput.value || null,
      metric_id: widgetUsesMetric.value ? widgetMetricIdInput.value || null : null,
      rolling_window_days: parseRollingWindow(widgetRollingWindowDaysInput.value),
      title: widgetTitleInput.value,
      widget_type: widgetTypeInput.value,
    });
    if (created) {
      widgetDialogVisible.value = false;
      successMessage.value = "Widget added.";
      snapshotWidgetLayouts();
    }
    return;
  }

  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetEditId.value, {
    rolling_window_days: parseRollingWindow(widgetRollingWindowDaysInput.value),
    title: widgetTitleInput.value,
  });
  if (updated) {
    widgetDialogVisible.value = false;
    successMessage.value = "Widget updated.";
  }
}

async function removeWidget(widgetId: string): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }
  const widget = selectedDashboard.value.widgets.find((candidate) => candidate.id === widgetId);
  if (widget === undefined) {
    return;
  }
  if (!window.confirm(`Remove widget "${widget.title}"?`)) {
    return;
  }

  resetMessages();
  const deleted = await dashboardsStore.deleteWidget(selectedDashboard.value.id, widgetId);
  if (deleted) {
    successMessage.value = "Widget removed.";
    snapshotWidgetLayouts();
  }
}

function layoutsOverlap(first: WidgetLayoutDraft, second: WidgetLayoutDraft): boolean {
  return !(
    first.grid_x + first.grid_w <= second.grid_x ||
    second.grid_x + second.grid_w <= first.grid_x ||
    first.grid_y + first.grid_h <= second.grid_y ||
    second.grid_y + second.grid_h <= first.grid_y
  );
}

function wouldOverlap(widgetId: string, candidate: WidgetLayoutDraft): boolean {
  return orderedWidgets.value.some((widget) => {
    if (widget.id === widgetId) {
      return false;
    }
    return layoutsOverlap(candidate, getWidgetLayout(widget));
  });
}

function clampLayout(candidate: WidgetLayoutDraft): WidgetLayoutDraft {
  const clampedWidth = Math.max(1, Math.min(GRID_COLUMNS, candidate.grid_w));
  const clampedHeight = Math.max(1, Math.min(MAX_WIDGET_HEIGHT, candidate.grid_h));
  const clampedX = Math.max(0, Math.min(GRID_COLUMNS - clampedWidth, candidate.grid_x));
  return {
    grid_h: clampedHeight,
    grid_w: clampedWidth,
    grid_x: clampedX,
    grid_y: Math.max(0, candidate.grid_y),
  };
}

function startInteraction(
  event: PointerEvent,
  widget: DashboardWidgetSummary,
  kind: "drag" | "resize",
): void {
  if (!editMode.value) {
    return;
  }

  event.preventDefault();
  resetMessages();
  activeInteraction.value = {
    kind,
    start_client_x: event.clientX,
    start_client_y: event.clientY,
    start_layout: { ...getWidgetLayout(widget) },
    widget_id: widget.id,
  };
  window.addEventListener("pointermove", handlePointerMove);
  window.addEventListener("pointerup", handlePointerUp);
}

function handlePointerMove(event: PointerEvent): void {
  if (activeInteraction.value === null || columnWidth.value === 0) {
    return;
  }

  const deltaColumns = Math.round((event.clientX - activeInteraction.value.start_client_x) / columnWidth.value);
  const deltaRows = Math.round((event.clientY - activeInteraction.value.start_client_y) / GRID_ROW_HEIGHT_PX);

  let candidate: WidgetLayoutDraft;
  if (activeInteraction.value.kind === "drag") {
    candidate = clampLayout({
      ...activeInteraction.value.start_layout,
      grid_x: activeInteraction.value.start_layout.grid_x + deltaColumns,
      grid_y: activeInteraction.value.start_layout.grid_y + deltaRows,
    });
  } else {
    candidate = clampLayout({
      ...activeInteraction.value.start_layout,
      grid_w: activeInteraction.value.start_layout.grid_w + deltaColumns,
      grid_h: activeInteraction.value.start_layout.grid_h + deltaRows,
    });
  }

  if (wouldOverlap(activeInteraction.value.widget_id, candidate)) {
    return;
  }

  localLayouts.value = {
    ...localLayouts.value,
    [activeInteraction.value.widget_id]: candidate,
  };
}

async function persistWidgetLayout(widgetId: string): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  const layout = localLayouts.value[widgetId];
  if (layout === undefined) {
    return;
  }

  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetId, layout);
  if (!updated) {
    snapshotWidgetLayouts();
    return;
  }
  successMessage.value = "Widget layout saved.";
}

function stopInteraction(): void {
  activeInteraction.value = null;
  window.removeEventListener("pointermove", handlePointerMove);
  window.removeEventListener("pointerup", handlePointerUp);
}

function handlePointerUp(): void {
  if (activeInteraction.value === null) {
    return;
  }

  const widgetId = activeInteraction.value.widget_id;
  stopInteraction();
  void persistWidgetLayout(widgetId);
}

watch(
  () => dashboardsStore.dashboards,
  () => {
    syncSelectedDashboard();
    snapshotWidgetLayouts();
  },
  { deep: true, immediate: true },
);

watch(
  () => selectedDashboardId.value,
  () => {
    snapshotWidgetLayouts();
  },
);

watch(
  () => gridHost.value,
  (element) => {
    resizeObserver?.disconnect();
    resizeObserver = null;
    if (element === null) {
      gridWidth.value = 0;
      return;
    }
    refreshGridMetrics();
    resizeObserver = new ResizeObserver(() => {
      refreshGridMetrics();
    });
    resizeObserver.observe(element);
  },
  { immediate: true },
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
    if (!activeMetricIds.has(widgetMetricIdInput.value)) {
      widgetMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

watch(
  () => goalsStore.goals,
  () => {
    const goalIds = new Set(goalsStore.goals.map((goal) => goal.id));
    if (!goalIds.has(widgetGoalIdInput.value)) {
      widgetGoalIdInput.value = goalsStore.goals[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

onMounted(() => {
  refreshGridMetrics();
  window.addEventListener("resize", refreshGridMetrics);
});

onBeforeUnmount(() => {
  stopInteraction();
  resizeObserver?.disconnect();
  window.removeEventListener("resize", refreshGridMetrics);
});
</script>

<template>
  <section class="dashboard-shell">
    <div class="dashboard-toolbar panel-card">
      <div class="toolbar-actions">
        <Dropdown
          v-model="selectedDashboardId"
          :options="dashboardOptions"
          option-label="label"
          option-value="value"
          placeholder="Select dashboard"
          class="dashboard-picker"
          :disabled="dashboardsStore.dashboards.length === 0"
        />
        <Button label="New dashboard" icon="pi pi-plus" @click="openCreateDashboardDialog" />
        <Button
          v-if="selectedDashboard !== null"
          :label="editMode ? 'Exit edit mode' : 'Edit dashboard'"
          :icon="editMode ? 'pi pi-check' : 'pi pi-pencil'"
          @click="editMode ? exitEditMode() : enterEditMode()"
        />
        <Button
          v-if="selectedDashboard !== null"
          label="Edit info"
          icon="pi pi-file-edit"
          severity="secondary"
          outlined
          @click="openEditDashboardDialog"
        />
        <Button
          v-if="selectedDashboard !== null && editMode"
          label="Add widget"
          icon="pi pi-plus-circle"
          severity="secondary"
          @click="openCreateWidgetDialog"
        />
        <Button
          v-if="selectedDashboard !== null && editMode && !selectedDashboard.is_default"
          label="Make default"
          icon="pi pi-star"
          severity="secondary"
          outlined
          @click="makeDashboardDefault"
        />
        <Button
          v-if="selectedDashboard !== null && editMode"
          label="Delete dashboard"
          icon="pi pi-trash"
          severity="danger"
          outlined
          @click="removeDashboard"
        />
      </div>
    </div>

    <Message v-if="successMessage !== ''" severity="success" :closable="false">
      {{ successMessage }}
    </Message>
    <Message v-if="dashboardsStore.errorMessage !== ''" severity="error" :closable="false">
      {{ dashboardsStore.errorMessage }}
    </Message>

    <div v-if="dashboardsStore.viewState === 'loading'" class="panel-card loading-panel">
      <ProgressSpinner strokeWidth="5" style="width: 2rem; height: 2rem" animationDuration=".8s" />
      <span>Loading dashboards.</span>
    </div>

    <div v-else-if="selectedDashboard !== null" class="dashboard-view">
      <div class="dashboard-summary panel-card">
        <div>
          <div class="dashboard-title-row">
            <h3>{{ selectedDashboard.name }}</h3>
            <Tag v-if="selectedDashboard.is_default" value="Default" severity="success" />
            <Tag v-if="editMode" value="Edit mode" severity="info" />
          </div>
          <p v-if="selectedDashboard.description !== null" class="dashboard-description">
            {{ selectedDashboard.description }}
          </p>
        </div>
      </div>

      <div
        v-if="orderedWidgets.length > 0"
        ref="gridHost"
        class="widget-grid"
        :class="{ editing: editMode }"
      >
        <article
          v-for="widget in orderedWidgets"
          :key="widget.id"
          class="panel-card widget-card"
          :class="{ active: activeInteraction?.widget_id === widget.id, editable: editMode }"
          :style="widgetGridStyle(widget)"
        >
          <div class="widget-card-header">
            <div>
              <p class="panel-eyebrow">{{ formatWidgetType(widget.widget_type) }}</p>
              <h4>{{ widget.title }}</h4>
              <p class="widget-subject">{{ widgetSubjectLabel(widget) }}</p>
            </div>

            <div class="widget-card-actions">
              <Tag
                v-if="widget.goal !== null"
                :value="widget.target_met ? 'On target' : 'Tracking'"
                :severity="widget.target_met ? 'success' : 'info'"
              />
              <button
                v-if="editMode"
                class="widget-icon-button widget-move-handle"
                type="button"
                title="Drag widget"
                @pointerdown="startInteraction($event, widget, 'drag')"
              >
                <i class="pi pi-arrows-alt" />
              </button>
              <button
                v-if="editMode"
                class="widget-icon-button"
                type="button"
                title="Edit widget"
                @click="openEditWidgetDialog(widget)"
              >
                <i class="pi pi-cog" />
              </button>
              <button
                v-if="editMode"
                class="widget-icon-button widget-delete-button"
                type="button"
                title="Remove widget"
                @click="void removeWidget(widget.id)"
              >
                <i class="pi pi-trash" />
              </button>
            </div>
          </div>

          <p v-if="widget.metric !== null" class="widget-summary">
            Latest value: <strong>{{ formatMetricValue(widget) }}</strong>
          </p>
          <p v-else class="widget-summary">
            {{ goalProgressLabel(widget) }}
          </p>

          <p v-if="widget.goal !== null" class="widget-meta">
            Goal window: {{ widget.goal.start_date }}
            <span v-if="widget.goal.target_date !== null"> to {{ widget.goal.target_date }}</span>
          </p>
          <p v-else-if="widget.metric?.latest_entry !== null" class="widget-meta">
            Last update: {{ formatTimestampInBrowserTimezone(widget.metric.latest_entry.recorded_at) }}
          </p>

          <DashboardWidgetChart :widget="widget" />

          <div v-if="editMode" class="widget-layout-meta">
            {{ getWidgetLayout(widget).grid_w }} x {{ getWidgetLayout(widget).grid_h }}
          </div>
          <button
            v-if="editMode"
            class="widget-resize-handle"
            type="button"
            title="Resize widget"
            @pointerdown="startInteraction($event, widget, 'resize')"
          >
            <i class="pi pi-arrow-down-right" />
          </button>
        </article>
      </div>

      <div v-else class="panel-card empty-panel">
        <p class="panel-eyebrow">No widgets yet</p>
        <h3>{{ editMode ? "Add the first widget for this dashboard." : "This dashboard is empty." }}</h3>
        <p>
          {{
            editMode
              ? "Use the Add widget button in the toolbar to start composing the layout."
              : "Enter edit mode to build this dashboard."
          }}
        </p>
      </div>
    </div>

    <div v-else class="panel-card empty-panel">
      <p class="panel-eyebrow">Dashboards</p>
      <h3>No dashboards yet</h3>
      <p>Create your first dashboard from the toolbar to start arranging widgets.</p>
    </div>

    <Dialog
      v-model:visible="dashboardDialogVisible"
      modal
      :header="dashboardDialogMode === 'create' ? 'Create dashboard' : 'Edit dashboard info'"
      :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    >
      <div class="dialog-form">
        <label class="field">
          <span class="label">Name</span>
          <InputText v-model="dashboardNameInput" placeholder="Morning check-in" />
        </label>
        <label class="field">
          <span class="label">Description</span>
          <textarea
            v-model="dashboardDescriptionInput"
            class="native-textarea"
            rows="4"
            placeholder="Optional summary for this dashboard"
          />
        </label>
        <div class="dialog-actions">
          <Button
            :label="dashboardDialogMode === 'create' ? 'Create dashboard' : 'Save dashboard'"
            icon="pi pi-save"
            :loading="dashboardsStore.submissionState === 'submitting'"
            @click="void submitDashboardDialog()"
          />
        </div>
      </div>
    </Dialog>

    <Dialog
      v-model:visible="widgetDialogVisible"
      modal
      :header="widgetDialogMode === 'create' ? 'Add widget' : 'Edit widget'"
      :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    >
      <div class="dialog-form widget-dialog-form">
        <div class="widget-dialog-intro">
          <p class="panel-eyebrow">Widget setup</p>
          <p class="widget-dialog-copy">
            Choose what this widget tracks, then adjust the time window if the chart should focus
            on a shorter slice of history.
          </p>
        </div>

        <label class="field widget-field">
          <span class="label">Title</span>
          <InputText v-model="widgetTitleInput" class="dialog-control" placeholder="Weight trend" />
        </label>

        <div class="widget-dialog-grid">
          <label class="field widget-field">
            <span class="label">Widget type</span>
            <Dropdown
              v-model="widgetTypeInput"
              :options="widgetTypeOptions"
              option-label="label"
              option-value="value"
              class="dialog-control"
              :disabled="widgetDialogMode === 'edit'"
            />
          </label>

          <label v-if="widgetUsesMetric" class="field widget-field">
            <span class="label">Metric</span>
            <Dropdown
              v-model="widgetMetricIdInput"
              :options="activeMetrics.map((metric) => ({ label: `${metric.name} (${metric.metric_type})`, value: metric.id }))"
              option-label="label"
              option-value="value"
              class="dialog-control"
              placeholder="Choose a metric"
              :disabled="widgetDialogMode === 'edit'"
            />
          </label>

          <label v-else class="field widget-field">
            <span class="label">Goal</span>
            <Dropdown
              v-model="widgetGoalIdInput"
              :options="goalsStore.goals.map((goal) => ({ label: goal.title, value: goal.id }))"
              option-label="label"
              option-value="value"
              class="dialog-control"
              placeholder="Choose a goal"
              :disabled="widgetDialogMode === 'edit'"
            />
          </label>
        </div>

        <label class="field widget-field">
          <span class="label">Rolling window days</span>
          <input
            v-model="widgetRollingWindowDaysInput"
            class="native-file-input dialog-control native-number-input"
            type="number"
            min="1"
            step="1"
            placeholder="Optional"
          />
          <span class="field-hint">
            Leave blank to use the full available history for this widget.
          </span>
        </label>

        <div class="dialog-actions widget-dialog-actions">
          <Button
            label="Cancel"
            severity="secondary"
            text
            @click="widgetDialogVisible = false"
          />
          <Button
            :label="widgetDialogMode === 'create' ? 'Add widget' : 'Save widget'"
            icon="pi pi-save"
            :loading="dashboardsStore.submissionState === 'submitting'"
            @click="void submitWidgetDialog()"
          />
        </div>
      </div>
    </Dialog>
  </section>
</template>

<style scoped>
.dashboard-shell {
  display: grid;
  gap: 1rem;
}

.dashboard-toolbar,
.dashboard-summary,
.widget-card,
.empty-panel,
.loading-panel {
  background: rgba(255, 255, 255, 0.94);
}

.dashboard-toolbar {
  display: flex;
  justify-content: flex-start;
  gap: 1rem;
  align-items: center;
}

.dashboard-description,
.widget-summary,
.widget-meta,
.widget-subject {
  color: #475569;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: center;
  gap: 0.75rem;
}

.dashboard-picker {
  min-width: 16rem;
}

.dashboard-view {
  display: grid;
  gap: 1rem;
}

.dashboard-summary {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.dashboard-title-row,
.widget-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.widget-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-rows: 6rem;
  gap: 1rem;
  align-items: stretch;
}

.widget-card {
  position: relative;
  display: grid;
  gap: 0.75rem;
  min-height: 0;
  overflow: hidden;
}

.widget-card.editable {
  border: 1px solid rgba(59, 130, 246, 0.25);
}

.widget-card.active {
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.widget-card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.widget-icon-button {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.92);
  color: #1e293b;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.widget-icon-button:hover {
  border-color: rgba(59, 130, 246, 0.45);
  color: #2563eb;
}

.widget-delete-button:hover {
  border-color: rgba(239, 68, 68, 0.45);
  color: #dc2626;
}

.widget-move-handle {
  cursor: move;
}

.widget-layout-meta {
  position: absolute;
  left: 1rem;
  bottom: 0.9rem;
  font-size: 0.75rem;
  color: #64748b;
  background: rgba(248, 250, 252, 0.9);
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
}

.widget-resize-handle {
  position: absolute;
  right: 0.65rem;
  bottom: 0.65rem;
  width: 2rem;
  height: 2rem;
  border: 0;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  border-radius: 0.75rem;
  display: grid;
  place-items: center;
  cursor: nwse-resize;
}

.dialog-form {
  display: grid;
  gap: 1rem;
}

.widget-dialog-form {
  gap: 1.2rem;
}

.widget-dialog-intro {
  display: grid;
  gap: 0.4rem;
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.95), rgba(248, 250, 252, 0.95));
  border: 1px solid rgba(191, 219, 254, 0.9);
}

.widget-dialog-copy,
.field-hint {
  color: #64748b;
}

.widget-dialog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.widget-field {
  display: grid;
  gap: 0.45rem;
}

.dialog-control {
  width: 100%;
}

.native-number-input {
  min-height: 2.85rem;
  border-radius: 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  padding: 0.7rem 0.9rem;
  background: #fff;
}

.widget-dialog-actions {
  justify-content: space-between;
  align-items: center;
  padding-top: 0.35rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
}

.loading-panel,
.empty-panel {
  display: grid;
  gap: 0.75rem;
}

@media (max-width: 1100px) {
  .dashboard-toolbar,
  .dashboard-summary {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 900px) {
  .widget-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .widget-card {
    grid-column: span 2 !important;
    grid-row: auto !important;
  }
}

@media (max-width: 640px) {
  .toolbar-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .dashboard-picker {
    min-width: 0;
    width: 100%;
  }

  .widget-grid {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
  }

  .widget-dialog-grid {
    grid-template-columns: 1fr;
  }

  .widget-dialog-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .widget-card {
    grid-column: auto !important;
    grid-row: auto !important;
  }
}
</style>
