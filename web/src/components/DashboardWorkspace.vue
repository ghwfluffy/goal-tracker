<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Dropdown from "primevue/dropdown";
import InputText from "primevue/inputtext";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import type { DashboardForecastAlgorithm, DashboardWidgetSummary } from "../lib/api";
import { useAppToast } from "../lib/toast";
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
const MOBILE_GRID_COLUMNS = 1;
const GRID_ROW_HEIGHT_PX = 96;
const MAX_WIDGET_HEIGHT = 12;
const MOBILE_LAYOUT_BREAKPOINT = "(max-width: 860px)";

const dashboardsStore = useDashboardsStore();
const metricsStore = useMetricsStore();
const goalsStore = useGoalsStore();
const { showSuccess } = useAppToast();

const selectedDashboardId = ref("");
const editMode = ref(false);
const dashboardPanelExpanded = ref(false);
const isMobileLayout = ref(false);

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
const widgetForecastAlgorithmInput = ref<DashboardForecastAlgorithm>("simple");

const gridHost = ref<HTMLElement | null>(null);
const gridWidth = ref(0);
const localLayouts = ref<Record<string, WidgetLayoutDraft>>({});
const activeInteraction = ref<WidgetInteractionState | null>(null);
let resizeObserver: ResizeObserver | null = null;
let mobileLayoutMediaQuery: MediaQueryList | null = null;

const dashboardOptions = computed(() => {
  return dashboardsStore.dashboards.map((dashboard) => ({
    label: dashboard.is_default ? `${dashboard.name} (Default)` : dashboard.name,
    value: dashboard.id,
  }));
});

const selectedDashboard = computed(() => {
  return dashboardsStore.dashboards.find((dashboard) => dashboard.id === selectedDashboardId.value) ?? null;
});

const activeLayoutMode = computed<"desktop" | "mobile">(() => {
  return isMobileLayout.value ? "mobile" : "desktop";
});

const activeGridColumns = computed(() => {
  return isMobileLayout.value ? MOBILE_GRID_COLUMNS : GRID_COLUMNS;
});

const layoutModeLabel = computed(() => {
  return isMobileLayout.value ? "Mobile layout" : "Desktop layout";
});

function layoutForMode(
  widget: DashboardWidgetSummary,
  layoutMode: "desktop" | "mobile" = activeLayoutMode.value,
): WidgetLayoutDraft {
  if (layoutMode === "mobile") {
    return {
      grid_h: widget.mobile_grid_h ?? widget.grid_h,
      grid_w: widget.mobile_grid_w ?? 1,
      grid_x: widget.mobile_grid_x ?? 0,
      grid_y: widget.mobile_grid_y ?? widget.grid_y,
    };
  }

  return {
    grid_h: widget.grid_h,
    grid_w: widget.grid_w,
    grid_x: widget.grid_x,
    grid_y: widget.grid_y,
  };
}

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

const activeGoals = computed(() => {
  return goalsStore.goals.filter((goal) => !goal.is_archived);
});

const widgetTypeOptions = [
  { label: "Metric summary", value: "metric_summary" },
  { label: "Metric history", value: "metric_history" },
  { label: "Days since", value: "days_since" },
  { label: "Goal progress", value: "goal_progress" },
  { label: "Goal success percent", value: "goal_success_percent" },
  { label: "Goal completion percent", value: "goal_completion_percent" },
  { label: "Goal failure risk", value: "goal_failure_risk" },
] satisfies Array<{ label: string; value: WidgetType }>;

const widgetForecastAlgorithmOptions = [
  { label: "Simple", value: "simple" },
  { label: "Weighted week-over-week", value: "weighted_week_over_week" },
  { label: "Weighted day-over-day", value: "weighted_day_over_day" },
] satisfies Array<{ label: string; value: DashboardForecastAlgorithm }>;

const widgetUsesMetric = computed(() => {
  return (
    widgetTypeInput.value === "metric_history" ||
    widgetTypeInput.value === "metric_summary" ||
    widgetTypeInput.value === "days_since"
  );
});

const availableWidgetMetrics = computed(() => {
  if (widgetTypeInput.value === "days_since") {
    return activeMetrics.value.filter((metric) => metric.metric_type === "date");
  }
  return activeMetrics.value;
});

const columnWidth = computed(() => {
  if (gridWidth.value <= 0) {
    return 0;
  }
  return gridWidth.value / activeGridColumns.value;
});

const widgetGridInlineStyle = computed(() => {
  return {
    gridTemplateColumns: `repeat(${activeGridColumns.value}, minmax(0, 1fr))`,
  };
});

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
    (selectedDashboard.value?.widgets ?? []).map((widget) => [widget.id, layoutForMode(widget)]),
  );
}

function refreshGridMetrics(): void {
  gridWidth.value = gridHost.value?.clientWidth ?? 0;
}

function getWidgetLayout(widget: DashboardWidgetSummary): WidgetLayoutDraft {
  return localLayouts.value[widget.id] ?? layoutForMode(widget);
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

function openCreateDashboardDialog(): void {
  dashboardDialogMode.value = "create";
  dashboardNameInput.value = "";
  dashboardDescriptionInput.value = "";
  dashboardDialogVisible.value = true;
}

function openEditDashboardDialog(): void {
  if (selectedDashboard.value === null) {
    return;
  }

  dashboardDialogMode.value = "edit";
  dashboardNameInput.value = selectedDashboard.value.name;
  dashboardDescriptionInput.value = selectedDashboard.value.description ?? "";
  dashboardDialogVisible.value = true;
}

function handleDashboardPanelToggle(event: Event): void {
  dashboardPanelExpanded.value = (event.currentTarget as HTMLDetailsElement).open;
}

function syncMobileLayout(mediaQuery: MediaQueryList | MediaQueryListEvent): void {
  const wasMobileLayout = isMobileLayout.value;
  isMobileLayout.value = mediaQuery.matches;
  if (wasMobileLayout !== isMobileLayout.value) {
    snapshotWidgetLayouts();
  }
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
      showSuccess("Dashboard created.", "Dashboards");
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
    showSuccess("Dashboard updated.", "Dashboards");
  }
}

async function makeDashboardDefault(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  const updated = await dashboardsStore.updateDashboard(selectedDashboard.value.id, {
    make_default: true,
  });
  if (updated) {
    showSuccess("Default dashboard updated.", "Dashboards");
  }
}

async function removeDashboard(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }
  if (!window.confirm(`Delete dashboard "${selectedDashboard.value.name}"?`)) {
    return;
  }

  const deleted = await dashboardsStore.deleteDashboard(selectedDashboard.value.id);
  if (deleted) {
    editMode.value = false;
    showSuccess("Dashboard deleted.", "Dashboards");
  }
}

function enterEditMode(): void {
  if (selectedDashboard.value === null) {
    return;
  }
  snapshotWidgetLayouts();
  editMode.value = true;
}

function exitEditMode(): void {
  editMode.value = false;
  stopInteraction();
  snapshotWidgetLayouts();
}

function openCreateWidgetDialog(): void {
  widgetDialogMode.value = "create";
  widgetEditId.value = "";
  widgetTitleInput.value = "";
  widgetTypeInput.value = "metric_summary";
  widgetMetricIdInput.value = availableWidgetMetrics.value[0]?.id ?? "";
  widgetGoalIdInput.value = activeGoals.value[0]?.id ?? "";
  widgetRollingWindowDaysInput.value = "30";
  widgetForecastAlgorithmInput.value = "simple";
  widgetDialogVisible.value = true;
}

function openEditWidgetDialog(widget: DashboardWidgetSummary): void {
  widgetDialogMode.value = "edit";
  widgetEditId.value = widget.id;
  widgetTitleInput.value = widget.title;
  widgetTypeInput.value = widget.widget_type;
  widgetMetricIdInput.value = widget.metric?.id ?? "";
  widgetGoalIdInput.value = widget.goal?.id ?? "";
  widgetRollingWindowDaysInput.value =
    widget.rolling_window_days === null ? "" : String(widget.rolling_window_days);
  widgetForecastAlgorithmInput.value = widget.forecast_algorithm ?? "simple";
  widgetDialogVisible.value = true;
}

const selectedWidgetGoal = computed(() => {
  if (widgetUsesMetric.value) {
    return null;
  }
  return activeGoals.value.find((goal) => goal.id === widgetGoalIdInput.value) ?? null;
});

const widgetUsesGoalTimeline = computed(() => {
  return !widgetUsesMetric.value && selectedWidgetGoal.value?.target_date !== null;
});

const widgetSupportsForecast = computed(() => {
  return (
    widgetTypeInput.value === "goal_progress" &&
    selectedWidgetGoal.value?.metric.metric_type === "number" &&
    selectedWidgetGoal.value?.target_value_number !== null
  );
});

async function submitWidgetDialog(): Promise<void> {
  if (selectedDashboard.value === null) {
    return;
  }

  if (widgetDialogMode.value === "create") {
    const created = await dashboardsStore.createWidget(selectedDashboard.value.id, {
      goal_id: widgetUsesMetric.value ? null : widgetGoalIdInput.value || null,
      forecast_algorithm: widgetSupportsForecast.value ? widgetForecastAlgorithmInput.value : null,
      metric_id: widgetUsesMetric.value ? widgetMetricIdInput.value || null : null,
      rolling_window_days: widgetUsesGoalTimeline.value ? null : parseRollingWindow(widgetRollingWindowDaysInput.value),
      title: widgetTitleInput.value,
      widget_type: widgetTypeInput.value,
    });
    if (created) {
      widgetDialogVisible.value = false;
      showSuccess("Widget added.", "Dashboards");
      snapshotWidgetLayouts();
    }
    return;
  }

  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetEditId.value, {
    forecast_algorithm: widgetSupportsForecast.value ? widgetForecastAlgorithmInput.value : null,
    rolling_window_days: widgetUsesGoalTimeline.value ? null : parseRollingWindow(widgetRollingWindowDaysInput.value),
    title: widgetTitleInput.value,
  });
  if (updated) {
    widgetDialogVisible.value = false;
    showSuccess("Widget updated.", "Dashboards");
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

  const deleted = await dashboardsStore.deleteWidget(selectedDashboard.value.id, widgetId);
  if (deleted) {
    showSuccess("Widget removed.", "Dashboards");
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
  const maxColumns = activeGridColumns.value;
  const clampedWidth = Math.max(1, Math.min(maxColumns, candidate.grid_w));
  const clampedHeight = Math.max(1, Math.min(MAX_WIDGET_HEIGHT, candidate.grid_h));
  const clampedX = Math.max(0, Math.min(maxColumns - clampedWidth, candidate.grid_x));
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
  if (!editMode.value || isMobileLayout.value) {
    return;
  }

  event.preventDefault();
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

  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetId, {
    ...layout,
    layout_mode: activeLayoutMode.value,
  });
  if (!updated) {
    snapshotWidgetLayouts();
    return;
  }
  showSuccess("Widget layout saved.", "Dashboards");
}

function canMoveWidget(direction: "up" | "down", widgetId: string): boolean {
  const index = orderedWidgets.value.findIndex((widget) => widget.id === widgetId);
  if (index < 0) {
    return false;
  }
  if (direction === "up") {
    return index > 0;
  }
  return index < orderedWidgets.value.length - 1;
}

async function moveWidgetInMobileStack(widgetId: string, direction: "up" | "down"): Promise<void> {
  if (selectedDashboard.value === null || !isMobileLayout.value) {
    return;
  }

  const index = orderedWidgets.value.findIndex((widget) => widget.id === widgetId);
  if (index < 0) {
    return;
  }

  const currentWidget = orderedWidgets.value[index];
  const currentLayout = getWidgetLayout(currentWidget);
  const targetWidget = orderedWidgets.value[direction === "up" ? index - 1 : index + 1];
  if (targetWidget === undefined) {
    return;
  }

  const targetLayout = getWidgetLayout(targetWidget);
  const nextY =
    direction === "up"
      ? Math.max(0, targetLayout.grid_y - 1)
      : targetLayout.grid_y + targetLayout.grid_h + 1;

  const updated = await dashboardsStore.updateWidget(selectedDashboard.value.id, widgetId, {
    grid_h: currentLayout.grid_h,
    grid_y: nextY,
    layout_mode: "mobile",
  });
  if (!updated) {
    return;
  }

  snapshotWidgetLayouts();
  showSuccess("Widget order updated.", "Dashboards");
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
    if (selectedDashboard.value !== null) {
      dashboardPanelExpanded.value = false;
    }
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
      widgetMetricIdInput.value = availableWidgetMetrics.value[0]?.id ?? "";
    }
    if (!widgetUsesMetric.value && widgetGoalIdInput.value === "") {
      widgetGoalIdInput.value = activeGoals.value[0]?.id ?? "";
    }
    if (!widgetSupportsForecast.value) {
      widgetForecastAlgorithmInput.value = "simple";
    }
  },
  { immediate: true },
);

watch(
  () => metricsStore.metrics,
  () => {
    const activeMetricIds = new Set(availableWidgetMetrics.value.map((metric) => metric.id));
    if (!activeMetricIds.has(widgetMetricIdInput.value)) {
      widgetMetricIdInput.value = availableWidgetMetrics.value[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

watch(
  () => goalsStore.goals,
  () => {
    const goalIds = new Set(activeGoals.value.map((goal) => goal.id));
    if (!goalIds.has(widgetGoalIdInput.value)) {
      widgetGoalIdInput.value = activeGoals.value[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

onMounted(() => {
  refreshGridMetrics();
  mobileLayoutMediaQuery = window.matchMedia(MOBILE_LAYOUT_BREAKPOINT);
  syncMobileLayout(mobileLayoutMediaQuery);
  mobileLayoutMediaQuery.addEventListener("change", syncMobileLayout);
  window.addEventListener("resize", refreshGridMetrics);
});

onBeforeUnmount(() => {
  stopInteraction();
  resizeObserver?.disconnect();
  mobileLayoutMediaQuery?.removeEventListener("change", syncMobileLayout);
  window.removeEventListener("resize", refreshGridMetrics);
});
</script>

<template>
  <section class="dashboard-shell">
    <details
      class="dashboard-disclosure panel-card"
      :open="dashboardPanelExpanded || selectedDashboard === null"
      @toggle="handleDashboardPanelToggle"
    >
      <summary class="dashboard-disclosure-summary">
        <div class="dashboard-summary-row">
          <h3>{{ selectedDashboard?.name ?? "Dashboards" }}</h3>
          <Tag v-if="selectedDashboard?.is_default" value="Default" severity="success" />
        </div>
        <div class="dashboard-disclosure-meta">
          <Tag v-if="editMode" value="Edit mode" severity="info" />
          <i class="pi disclosure-chevron" :class="dashboardPanelExpanded ? 'pi-chevron-up' : 'pi-chevron-down'" />
        </div>
      </summary>

      <div class="dashboard-disclosure-body">
        <div class="dashboard-toolbar">
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

        <div v-if="selectedDashboard !== null" class="dashboard-summary">
          <div>
            <div class="dashboard-title-row">
              <Tag v-if="selectedDashboard.is_default" value="Default" severity="success" />
              <Tag v-if="editMode" value="Edit mode" severity="info" />
              <Tag :value="layoutModeLabel" severity="warning" />
            </div>
            <p v-if="selectedDashboard.description !== null" class="dashboard-description">
              {{ selectedDashboard.description }}
            </p>
            <p v-else class="dashboard-description">No description yet.</p>
            <p class="dashboard-layout-note">
              Widget moves and resizes currently save to the {{ layoutModeLabel.toLowerCase() }}.
            </p>
          </div>
        </div>
      </div>
    </details>

    <div v-if="dashboardsStore.viewState === 'loading'" class="panel-card loading-panel">
      <ProgressSpinner strokeWidth="5" style="width: 2rem; height: 2rem" animationDuration=".8s" />
      <span>Loading dashboards.</span>
    </div>

    <div v-else-if="selectedDashboard !== null" class="dashboard-view">
      <div
        v-if="orderedWidgets.length > 0"
        ref="gridHost"
        class="widget-grid"
        :class="{ editing: editMode }"
        :style="widgetGridInlineStyle"
      >
        <article
          v-for="widget in orderedWidgets"
          :key="widget.id"
          class="panel-card widget-card"
          :class="{ active: activeInteraction?.widget_id === widget.id, editable: editMode }"
          :style="widgetGridStyle(widget)"
        >
          <div class="widget-card-header">
            <h4>{{ widget.title }}</h4>

            <div class="widget-card-actions">
              <template v-if="editMode && isMobileLayout">
                <button
                  class="widget-icon-button"
                  type="button"
                  title="Move widget up"
                  :disabled="!canMoveWidget('up', widget.id)"
                  @click="void moveWidgetInMobileStack(widget.id, 'up')"
                >
                  <i class="pi pi-arrow-up" />
                </button>
                <button
                  class="widget-icon-button"
                  type="button"
                  title="Move widget down"
                  :disabled="!canMoveWidget('down', widget.id)"
                  @click="void moveWidgetInMobileStack(widget.id, 'down')"
                >
                  <i class="pi pi-arrow-down" />
                </button>
              </template>
              <button
                v-else-if="editMode"
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

          <DashboardWidgetChart :widget="widget" />

          <div v-if="editMode" class="widget-layout-meta">
            <template v-if="isMobileLayout">
              {{ layoutModeLabel }}: stacked
            </template>
            <template v-else>
              {{ layoutModeLabel }}: {{ getWidgetLayout(widget).grid_w }} x {{ getWidgetLayout(widget).grid_h }}
            </template>
          </div>
          <button
            v-if="editMode && !isMobileLayout"
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
              ? "Use the Add widget button in the dashboard controls panel to start composing the layout."
              : "Expand the dashboard controls panel and enter edit mode to build this dashboard."
          }}
        </p>
      </div>
    </div>

    <div v-else class="panel-card empty-panel">
      <p class="panel-eyebrow">Dashboards</p>
      <h3>No dashboards yet</h3>
      <p>Expand the dashboard controls panel and create your first dashboard.</p>
    </div>

    <Dialog
      v-model:visible="dashboardDialogVisible"
      modal
      :header="dashboardDialogMode === 'create' ? 'Create dashboard' : 'Edit dashboard info'"
      :style="{ width: 'min(34rem, calc(100vw - 2rem))' }"
    >
      <div class="dialog-form dashboard-dialog-form">
        <label class="field dialog-field">
          <span class="label">Name</span>
          <InputText
            v-model="dashboardNameInput"
            class="dialog-control"
            placeholder="Morning check-in"
          />
        </label>
        <label class="field dialog-field">
          <span class="label">Description</span>
          <textarea
            v-model="dashboardDescriptionInput"
            class="native-textarea dialog-control dashboard-description-input"
            rows="4"
            placeholder="Optional summary for this dashboard"
          />
        </label>
        <div class="dialog-actions dashboard-dialog-actions">
          <Button
            label="Cancel"
            severity="secondary"
            text
            @click="dashboardDialogVisible = false"
          />
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
              :options="availableWidgetMetrics.map((metric) => ({ label: `${metric.name} (${metric.metric_type})`, value: metric.id }))"
              option-label="label"
              option-value="value"
              class="dialog-control"
              placeholder="Choose a metric"
              :disabled="widgetDialogMode === 'edit'"
            />
            <span v-if="widgetTypeInput === 'days_since'" class="field-hint">
              Uses the latest metric date value and today in your profile timezone.
            </span>
          </label>

          <label v-else class="field widget-field">
            <span class="label">Goal</span>
            <Dropdown
              v-model="widgetGoalIdInput"
              :options="activeGoals.map((goal) => ({ label: goal.title, value: goal.id }))"
              option-label="label"
              option-value="value"
              class="dialog-control"
              placeholder="Choose a goal"
              :disabled="widgetDialogMode === 'edit'"
            />
          </label>
        </div>

        <label v-if="widgetSupportsForecast" class="field widget-field">
          <span class="label">Forecast algorithm</span>
          <Dropdown
            v-model="widgetForecastAlgorithmInput"
            :options="widgetForecastAlgorithmOptions"
            option-label="label"
            option-value="value"
            class="dialog-control"
          />
          <span class="field-hint">
            Historical data stays green, the projected now segment is blue, and the future forecast is red.
          </span>
        </label>
        <div
          v-else-if="widgetTypeInput === 'goal_progress' && !widgetUsesMetric && selectedWidgetGoal !== null"
          class="widget-dialog-note"
        >
          Forecast algorithms are available on numeric goal-progress widgets with a target value.
        </div>

        <label v-if="!widgetUsesGoalTimeline" class="field widget-field">
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
        <div v-else class="widget-dialog-note">
          Goal widgets with a target date always render the full start-to-end timeline.
        </div>

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
  gap: var(--space-6);
}

.dashboard-disclosure,
.dashboard-summary,
.widget-card,
.empty-panel,
.loading-panel {
  background: var(--color-surface-panel-strong);
}

.dashboard-disclosure {
  display: grid;
  gap: var(--space-3);
}

.dashboard-disclosure-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  cursor: pointer;
  list-style: none;
}

.dashboard-disclosure-summary::-webkit-details-marker {
  display: none;
}

.dashboard-summary-row,
.dashboard-disclosure-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.dashboard-summary-row {
  min-width: 0;
}

.dashboard-summary-row h3 {
  margin: 0;
  font-size: 1rem;
}

.dashboard-disclosure-meta {
  margin-left: auto;
}

.disclosure-chevron {
  font-size: 0.9rem;
  color: var(--color-text-faint);
}

.dashboard-disclosure-body {
  display: grid;
  gap: var(--space-4);
}

.dashboard-toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.dashboard-description {
  color: var(--color-text-subtle);
}

.dashboard-layout-note {
  margin-top: var(--space-3);
  color: var(--color-text-faint);
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: center;
  gap: var(--space-4);
}

.dashboard-picker {
  min-width: 16rem;
}

.dashboard-view {
  display: grid;
  gap: var(--space-6);
}

.dashboard-summary {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: flex-start;
}

.dashboard-title-row,
.widget-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.widget-grid {
  display: grid;
  grid-auto-rows: 6rem;
  gap: var(--space-6);
  align-items: stretch;
}

.widget-card {
  position: relative;
  display: grid;
  gap: 0.5rem;
  min-height: 0;
  overflow: hidden;
}

.widget-card.editable {
  border: 1px solid var(--color-border-interactive-soft);
}

.widget-card.active {
  box-shadow: var(--shadow-focus-soft);
}

.widget-card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.widget-card h4 {
  font-size: 1rem;
  line-height: 1.2;
}

.widget-icon-button {
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border-icon);
  background: var(--color-surface-panel-overlay);
  color: var(--color-text-default);
  display: grid;
  place-items: center;
  cursor: pointer;
}

.widget-icon-button:hover {
  border-color: var(--color-border-interactive);
  color: var(--color-text-link);
}

.widget-icon-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.widget-delete-button:hover {
  border-color: var(--color-border-danger-soft);
  color: var(--chart-series-danger);
}

.widget-move-handle {
  cursor: move;
}

.widget-layout-meta {
  position: absolute;
  left: var(--space-6);
  bottom: 0.9rem;
  font-size: var(--font-size-caption);
  color: var(--color-text-faint);
  background: var(--color-surface-muted-soft);
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-pill);
}

.widget-resize-handle {
  position: absolute;
  right: 0.65rem;
  bottom: 0.65rem;
  width: 2rem;
  height: 2rem;
  border: 0;
  background: var(--color-surface-interactive-soft);
  color: var(--color-text-link);
  border-radius: var(--radius-sm);
  display: grid;
  place-items: center;
  cursor: nwse-resize;
}

.dialog-form {
  display: grid;
  gap: var(--space-6);
}

.dashboard-dialog-form,
.widget-dialog-form {
  gap: var(--space-6);
}

.dialog-field,
.widget-field {
  display: grid;
  gap: var(--space-3);
}

.dialog-form :deep(.p-inputtext),
.dialog-form :deep(.p-dropdown) {
  width: 100%;
}

.field-hint,
.widget-dialog-note {
  color: var(--color-text-faint);
}

.widget-dialog-note {
  padding: 0.9rem 1rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border-soft);
}

.widget-dialog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-6);
}

@media (max-width: 900px) {
  .dashboard-disclosure-summary,
  .dashboard-summary,
  .dashboard-title-row {
    flex-direction: column;
  }

  .dashboard-disclosure-meta {
    margin-left: 0;
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 720px) {
  .dashboard-shell {
    gap: var(--space-4);
  }

  .dashboard-disclosure {
    padding: var(--space-4);
  }

  .dashboard-summary-row h3 {
    font-size: 0.95rem;
  }

  .dashboard-picker {
    min-width: 100%;
  }

  .dashboard-toolbar {
    align-items: stretch;
  }

  .toolbar-actions {
    gap: var(--space-2);
  }

  .toolbar-actions :deep(.p-button) {
    width: 100%;
    justify-content: center;
  }

  .dashboard-view {
    gap: var(--space-4);
    padding: 0 var(--space-3) var(--space-3);
  }

  .widget-grid {
    gap: var(--space-4);
  }

  .widget-dialog-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
