<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Menu from "primevue/menu";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import {
  isNumericMetricType,
  numberInputStep,
  parseDecimalPlaces,
  parseOptionalNumber,
} from "../../lib/tracking";
import { useAppToast } from "../../lib/toast";
import { useGoalsStore } from "../../stores/goals";
import { useMetricsStore } from "../../stores/metrics";
import ManagementToolbar from "./ManagementToolbar.vue";

type GoalType = "metric" | "checklist";

const emit = defineEmits<{
  openMetricEntry: [metricId: string];
  openMetricHistory: [metricId: string];
}>();

const goalsStore = useGoalsStore();
const metricsStore = useMetricsStore();

const goalRowMenu = ref<InstanceType<typeof Menu> | null>(null);
const activeGoalMenuId = ref("");
const goalDialogVisible = ref(false);
const goalDialogMode = ref<"create" | "edit">("create");
const goalEditId = ref("");
const viewMode = ref<"table" | "cards">("table");
const { showSuccess } = useAppToast();

const goalTypeInput = ref<GoalType>("metric");
const goalTitleInput = ref("");
const goalDescriptionInput = ref("");
const goalStartDateInput = ref(new Date().toISOString().slice(0, 10));
const goalTargetDateInput = ref("");
const goalTargetNumberValueInput = ref("");
const goalSuccessThresholdPercentInput = ref("100");
const goalExceptionDateInput = ref("");
const goalExceptionDates = ref<string[]>([]);
const goalChecklistItemInput = ref("");
const goalChecklistItems = ref<Array<{ id?: string | null; title: string }>>([]);
const goalUseNewMetric = ref(false);
const goalMetricIdInput = ref("");
const goalNewMetricNameInput = ref("");
const goalNewMetricTypeInput = ref<"number" | "count" | "date">("number");
const goalNewMetricDecimalPlacesInput = ref("0");
const goalNewMetricUnitLabelInput = ref("");
const goalNewMetricInitialNumberValueInput = ref("");
const goalNewMetricInitialDateValueInput = ref("");

const activeMetrics = computed(() => metricsStore.metrics.filter((metric) => !metric.is_archived));

const selectedGoalMetric = computed(() => {
  return activeMetrics.value.find((metric) => metric.id === goalMetricIdInput.value) ?? null;
});

const editingGoal = computed(() => {
  return goalsStore.goals.find((goal) => goal.id === goalEditId.value) ?? null;
});

const selectedGoalMenuGoal = computed(() => {
  return goalsStore.goals.find((goal) => goal.id === activeGoalMenuId.value) ?? null;
});

const goalIsChecklist = computed(() => {
  if (goalDialogMode.value === "edit") {
    return editingGoal.value?.goal_type === "checklist";
  }
  return goalTypeInput.value === "checklist";
});

const goalMetricType = computed(() => {
  if (goalIsChecklist.value) {
    return null;
  }
  if (goalDialogMode.value === "edit") {
    return editingGoal.value?.metric?.metric_type ?? "number";
  }
  if (goalUseNewMetric.value) {
    return goalNewMetricTypeInput.value;
  }

  return selectedGoalMetric.value?.metric_type ?? "number";
});

const goalMetricDecimalPlaces = computed(() => {
  if (goalIsChecklist.value) {
    return 0;
  }
  if (goalDialogMode.value === "edit") {
    return editingGoal.value?.metric?.decimal_places ?? 0;
  }
  if (goalUseNewMetric.value) {
    return parseDecimalPlaces(goalNewMetricDecimalPlacesInput.value);
  }
  return selectedGoalMetric.value?.decimal_places ?? 0;
});

const goalRowMenuItems = computed<MenuItem[]>(() => {
  const goal = selectedGoalMenuGoal.value;
  if (goal === null) {
    return [];
  }

  const items: MenuItem[] = [
    {
      icon: "pi pi-pencil",
      label: "Edit",
      command: () => openEditDialog(goal),
    },
  ];

  if (goal.metric !== null) {
    items.push(
      {
        icon: "pi pi-plus-circle",
        label: "Add metric update",
        command: () => emit("openMetricEntry", goal.metric!.id),
      },
      {
        icon: "pi pi-chart-line",
        label: "View metric history",
        command: () => emit("openMetricHistory", goal.metric!.id),
      },
    );
  }

  items.push(
    goal.is_archived
      ? {
          icon: "pi pi-refresh",
          label: "Restore",
          command: () => {
            void setGoalArchived(goal.id, false);
          },
        }
      : {
          icon: "pi pi-box",
          label: "Archive",
          command: () => {
            void setGoalArchived(goal.id, true);
          },
        },
  );

  return items;
});

function resetGoalForm(): void {
  goalTypeInput.value = "metric";
  goalTitleInput.value = "";
  goalDescriptionInput.value = "";
  goalStartDateInput.value = new Date().toISOString().slice(0, 10);
  goalTargetDateInput.value = "";
  goalTargetNumberValueInput.value = "";
  goalSuccessThresholdPercentInput.value = "100";
  goalExceptionDateInput.value = "";
  goalExceptionDates.value = [];
  goalChecklistItemInput.value = "";
  goalChecklistItems.value = [];
  goalUseNewMetric.value = false;
  goalMetricIdInput.value = activeMetrics.value[0]?.id ?? "";
  goalNewMetricNameInput.value = "";
  goalNewMetricTypeInput.value = "number";
  goalNewMetricDecimalPlacesInput.value = "0";
  goalNewMetricUnitLabelInput.value = "";
  goalNewMetricInitialNumberValueInput.value = "";
  goalNewMetricInitialDateValueInput.value = "";
}

function openCreateDialog(): void {
  goalDialogMode.value = "create";
  goalEditId.value = "";
  resetGoalForm();
  goalDialogVisible.value = true;
}

function openEditDialog(goal: (typeof goalsStore.goals)[number]): void {
  goalDialogMode.value = "edit";
  goalEditId.value = goal.id;
  goalTypeInput.value = goal.goal_type;
  goalTitleInput.value = goal.title;
  goalDescriptionInput.value = goal.description ?? "";
  goalStartDateInput.value = goal.start_date;
  goalTargetDateInput.value = goal.target_date ?? "";
  goalTargetNumberValueInput.value =
    goal.target_value_number === null ? "" : String(goal.target_value_number);
  goalSuccessThresholdPercentInput.value =
    goal.success_threshold_percent === null ? "100" : String(goal.success_threshold_percent);
  goalExceptionDateInput.value = "";
  goalExceptionDates.value = [...goal.exception_dates];
  goalChecklistItemInput.value = "";
  goalChecklistItems.value = goal.checklist_items.map((item) => ({ id: item.id, title: item.title }));
  goalUseNewMetric.value = false;
  goalMetricIdInput.value = goal.metric?.id ?? "";
  goalNewMetricNameInput.value = "";
  goalNewMetricTypeInput.value = goal.metric?.metric_type ?? "number";
  goalNewMetricDecimalPlacesInput.value = String(goal.metric?.decimal_places ?? 0);
  goalNewMetricUnitLabelInput.value = goal.metric?.unit_label ?? "";
  goalNewMetricInitialNumberValueInput.value = "";
  goalNewMetricInitialDateValueInput.value = "";
  goalDialogVisible.value = true;
}

function addGoalExceptionDate(): void {
  const candidate = goalExceptionDateInput.value;
  if (candidate === "") {
    return;
  }
  if (!goalExceptionDates.value.includes(candidate)) {
    goalExceptionDates.value = [...goalExceptionDates.value, candidate].sort();
  }
  goalExceptionDateInput.value = "";
}

function removeGoalExceptionDate(value: string): void {
  goalExceptionDates.value = goalExceptionDates.value.filter((candidate) => candidate !== value);
}

function addChecklistItem(): void {
  const title = goalChecklistItemInput.value.trim();
  if (title === "") {
    return;
  }
  goalChecklistItems.value = [...goalChecklistItems.value, { title }];
  goalChecklistItemInput.value = "";
}

function removeChecklistItem(index: number): void {
  goalChecklistItems.value = goalChecklistItems.value.filter((_, itemIndex) => itemIndex !== index);
}

function toggleGoalRowMenu(event: Event, goalId: string): void {
  activeGoalMenuId.value = goalId;
  goalRowMenu.value?.toggle(event);
}

function isDateGoal(goal: (typeof goalsStore.goals)[number]): boolean {
  return goal.metric?.metric_type === "date";
}

function formatGoalTargetSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.goal_type === "checklist") {
    const itemLabel = goal.checklist_total_count === 1 ? "item" : "items";
    return `${goal.checklist_total_count} ${itemLabel}`;
  }
  if (goal.metric !== null && isNumericMetricType(goal.metric.metric_type) && goal.target_value_number !== null) {
    return `${goal.target_value_number.toFixed(goal.metric.decimal_places ?? 0)}${
      goal.metric.unit_label !== null ? ` ${goal.metric.unit_label}` : ""
    }`;
  }
  if (goal.success_threshold_percent !== null) {
    return `${goal.success_threshold_percent}% success`;
  }
  return "No target";
}

function formatGoalCurrentProgressSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.current_progress_percent === null) {
    return goal.goal_type === "checklist" ? "0 done" : "No progress yet";
  }
  if (goal.goal_type === "checklist") {
    return `${goal.checklist_completed_count}/${goal.checklist_total_count} done (${goal.current_progress_percent}%)`;
  }
  if (isDateGoal(goal) && goal.target_met !== null) {
    return `${goal.current_progress_percent}% (${goal.target_met ? "on target" : "below target"})`;
  }
  return `${goal.current_progress_percent}%`;
}

function formatGoalSubjectSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.goal_type === "checklist") {
    return "Checklist";
  }
  if (goal.metric === null) {
    return "No metric";
  }
  return `${goal.metric.name} (${goal.metric.metric_type})`;
}

function formatGoalLatestMetricSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.goal_type === "checklist") {
    return `${goal.checklist_completed_count}/${goal.checklist_total_count} completed`;
  }
  if (goal.metric?.latest_entry === null || goal.metric === null) {
    return "No metric yet";
  }

  if (goal.metric.metric_type === "date") {
    return goal.metric.latest_entry.date_value ?? "No metric yet";
  }

  const numberValue = goal.metric.latest_entry.number_value;
  if (numberValue === null) {
    return "No metric yet";
  }

  const formatted = numberValue.toFixed(goal.metric.decimal_places ?? 0);
  return goal.metric.unit_label === null ? formatted : `${formatted} ${goal.metric.unit_label}`;
}

function goalStatusTagValue(goal: (typeof goalsStore.goals)[number]): string {
  return goal.is_archived ? "archived" : goal.status;
}

function goalStatusTagSeverity(goal: (typeof goalsStore.goals)[number]): "success" | "warning" {
  return goal.is_archived ? "warning" : "success";
}

async function submitGoalForm(): Promise<void> {
  const isChecklistGoal = goalIsChecklist.value;
  if (goalDialogMode.value === "create") {
    const created = await goalsStore.createGoal({
      checklist_items: isChecklistGoal ? goalChecklistItems.value : [],
      description: goalDescriptionInput.value.trim() === "" ? null : goalDescriptionInput.value,
      exception_dates: !isChecklistGoal && goalMetricType.value === "date" ? goalExceptionDates.value : [],
      goal_type: isChecklistGoal ? "checklist" : "metric",
      metric_id: !isChecklistGoal && !goalUseNewMetric.value ? goalMetricIdInput.value || null : null,
      new_metric:
        !isChecklistGoal && goalUseNewMetric.value
          ? {
              decimal_places:
                isNumericMetricType(goalNewMetricTypeInput.value)
                  ? parseDecimalPlaces(goalNewMetricDecimalPlacesInput.value)
                  : null,
              initial_date_value:
                goalNewMetricTypeInput.value === "date"
                  ? goalNewMetricInitialDateValueInput.value || null
                  : null,
              initial_number_value:
                isNumericMetricType(goalNewMetricTypeInput.value)
                  ? parseOptionalNumber(goalNewMetricInitialNumberValueInput.value)
                  : null,
              metric_type: goalNewMetricTypeInput.value,
              name: goalNewMetricNameInput.value,
              unit_label:
                goalNewMetricUnitLabelInput.value.trim() === ""
                  ? null
                  : goalNewMetricUnitLabelInput.value,
            }
          : null,
      start_date: goalStartDateInput.value,
      success_threshold_percent:
        !isChecklistGoal && goalMetricType.value === "date"
          ? parseOptionalNumber(goalSuccessThresholdPercentInput.value)
          : null,
      target_date: goalTargetDateInput.value || null,
      target_value_date: null,
      target_value_number:
        !isChecklistGoal && goalMetricType.value !== null && isNumericMetricType(goalMetricType.value)
          ? parseOptionalNumber(goalTargetNumberValueInput.value)
          : null,
      title: goalTitleInput.value,
    });

    if (!created) {
      return;
    }

    showSuccess("Goal created.", "Goals");
    goalDialogVisible.value = false;
    resetGoalForm();
    if (!isChecklistGoal) {
      await metricsStore.loadMetrics();
    }
    return;
  }

  if (editingGoal.value === null) {
    return;
  }

  const updated = await goalsStore.updateGoalDetails(editingGoal.value.id, {
    checklist_items: isChecklistGoal ? goalChecklistItems.value : undefined,
    description: goalDescriptionInput.value.trim() === "" ? null : goalDescriptionInput.value,
    exception_dates: !isChecklistGoal && goalMetricType.value === "date" ? goalExceptionDates.value : [],
    start_date: goalStartDateInput.value,
    success_threshold_percent:
      !isChecklistGoal && goalMetricType.value === "date"
        ? parseOptionalNumber(goalSuccessThresholdPercentInput.value)
        : null,
    target_date: goalTargetDateInput.value || null,
    target_value_date: null,
    target_value_number:
      !isChecklistGoal && goalMetricType.value !== null && isNumericMetricType(goalMetricType.value)
        ? parseOptionalNumber(goalTargetNumberValueInput.value)
        : null,
    title: goalTitleInput.value,
  });
  if (!updated) {
    return;
  }

  showSuccess("Goal updated.", "Goals");
  goalDialogVisible.value = false;
  goalEditId.value = "";
}

async function setGoalArchived(goalId: string, archived: boolean): Promise<void> {
  const updated = await goalsStore.setGoalArchived(goalId, archived);
  if (!updated) {
    return;
  }

  showSuccess(archived ? "Goal archived." : "Goal restored.", "Goals");
}

function toggleIncludeArchived(): void {
  goalsStore.includeArchived = !goalsStore.includeArchived;
  void goalsStore.loadGoals();
}
</script>

<template>
  <div class="management-shell">
    <ManagementToolbar
      v-model:viewMode="viewMode"
      title="Manage goals"
      description="Goals can be metric-driven targets or simple checklists with a target date, and both can be used on dashboards."
      primary-action-label="Add goal"
      :primary-action-loading="goalsStore.submissionState === 'submitting'"
      @add="openCreateDialog"
    >
      <template #leading-actions>
        <Button
          label="Archived"
          icon="pi pi-box"
          severity="secondary"
          :outlined="!goalsStore.includeArchived"
          class="toolbar-filter-button"
          aria-label="Toggle archived goals"
          @click="toggleIncludeArchived"
        />
      </template>
    </ManagementToolbar>

    <div v-if="goalsStore.viewState === 'loading'" class="panel-card loading">
      <ProgressSpinner strokeWidth="5" style="width: 2rem; height: 2rem" animationDuration=".8s" />
      <span>Loading goals.</span>
    </div>

    <div v-else-if="goalsStore.goals.length === 0" class="panel-card empty-state">
      No goals yet.
    </div>

    <div v-else-if="viewMode === 'table'" class="tracking-table-wrap panel-card">
      <table class="tracking-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Progress</th>
            <th>Target</th>
            <th class="mobile-hide-column">Subject</th>
            <th class="mobile-hide-column">Start</th>
            <th class="mobile-hide-column">Failure risk</th>
            <th class="mobile-hide-column">Status</th>
            <th class="table-actions-column">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="goal in goalsStore.goals" :key="goal.id">
            <td>
              <div class="table-primary-cell">
                <strong>{{ goal.title }}</strong>
              </div>
            </td>
            <td>{{ formatGoalCurrentProgressSummary(goal) }}</td>
            <td>
              <div class="table-primary-cell">
                <span>{{ formatGoalTargetSummary(goal) }}</span>
                <span v-if="goal.target_date !== null" class="table-secondary-text">
                  By {{ goal.target_date }}
                </span>
              </div>
            </td>
            <td class="mobile-hide-column">{{ formatGoalSubjectSummary(goal) }}</td>
            <td class="mobile-hide-column">{{ goal.start_date }}</td>
            <td class="mobile-hide-column">
              {{ goal.failure_risk_percent === null ? "n/a" : `${goal.failure_risk_percent}%` }}
            </td>
            <td class="mobile-hide-column">
              <Tag :value="goalStatusTagValue(goal)" :severity="goalStatusTagSeverity(goal)" />
            </td>
            <td class="table-kebab-cell">
              <Button
                icon="pi pi-ellipsis-v"
                text
                rounded
                aria-label="Goal actions"
                @click="toggleGoalRowMenu($event, goal.id)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="management-card-grid">
      <article v-for="goal in goalsStore.goals" :key="goal.id" class="tracking-card">
        <div class="tracking-card-header">
          <div>
            <h3>{{ goal.title }}</h3>
            <p v-if="goal.description !== null">{{ goal.description }}</p>
          </div>
          <div class="card-header-actions">
            <Tag :value="goalStatusTagValue(goal)" :severity="goalStatusTagSeverity(goal)" />
            <Button
              icon="pi pi-ellipsis-v"
              text
              rounded
              aria-label="Goal actions"
              @click="toggleGoalRowMenu($event, goal.id)"
            />
          </div>
        </div>

        <div class="goal-meta-grid">
          <div class="history-row">
            <strong>Subject</strong>
            <span>{{ formatGoalSubjectSummary(goal) }}</span>
          </div>
          <div class="history-row">
            <strong>Start</strong>
            <span>{{ goal.start_date }}</span>
          </div>
          <div class="history-row">
            <strong>Target</strong>
            <span>{{ formatGoalTargetSummary(goal) }}</span>
          </div>
          <div class="history-row" v-if="goal.target_date !== null">
            <strong>Target date</strong>
            <span>{{ goal.target_date }}</span>
          </div>
          <div class="history-row">
            <strong>Current progress</strong>
            <span>{{ formatGoalCurrentProgressSummary(goal) }}</span>
          </div>
          <div class="history-row" v-if="goal.time_progress_percent !== null">
            <strong>Time progress</strong>
            <span>{{ goal.time_progress_percent }}%</span>
          </div>
          <div class="history-row" v-if="goal.failure_risk_percent !== null">
            <strong>Failure risk</strong>
            <span>{{ goal.failure_risk_percent }}%</span>
          </div>
          <div class="history-row" v-if="goal.exception_dates.length > 0">
            <strong>Exception dates</strong>
            <span>{{ goal.exception_dates.join(", ") }}</span>
          </div>
          <div class="history-row">
            <strong>{{ goal.goal_type === "checklist" ? "Checklist" : "Latest metric" }}</strong>
            <span>{{ formatGoalLatestMetricSummary(goal) }}</span>
          </div>
        </div>

        <div v-if="goal.goal_type === 'checklist' && goal.checklist_items.length > 0" class="goal-checklist-preview">
          <div
            v-for="item in goal.checklist_items"
            :key="item.id"
            class="goal-checklist-preview-item"
            :class="{ completed: item.is_completed }"
          >
            <i :class="item.is_completed ? 'pi pi-check-square' : 'pi pi-square'" />
            <span>{{ item.title }}</span>
          </div>
        </div>
      </article>
    </div>

    <Menu ref="goalRowMenu" :model="goalRowMenuItems" popup />

    <Dialog
      v-model:visible="goalDialogVisible"
      modal
      :header="goalDialogMode === 'create' ? 'Add goal' : 'Edit goal'"
      class="profile-dialog"
      :style="{ width: 'min(42rem, 96vw)' }"
    >
      <div class="dialog-stack">
        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>{{ goalDialogMode === "create" ? "Create a goal" : "Edit goal" }}</h3>
            <p v-if="goalDialogMode === 'create'">
              Use a metric goal for measured targets or a checklist goal for task-based work like cleaning the house.
            </p>
            <p v-else>
              Update the goal details here. Goal type and any linked metric stay fixed after creation.
            </p>
          </div>

          <div class="form-stack">
            <template v-if="goalDialogMode === 'create'">
              <label class="field">
                <span class="label">Goal type</span>
                <select v-model="goalTypeInput" class="native-file-input">
                  <option value="metric">Metric goal</option>
                  <option value="checklist">Checklist goal</option>
                </select>
              </label>
            </template>
            <div v-else class="widget-dialog-note">
              Type: {{ editingGoal?.goal_type === "checklist" ? "Checklist goal" : "Metric goal" }}
            </div>

            <label class="field">
              <span class="label">Goal title</span>
              <InputText v-model="goalTitleInput" />
            </label>

            <label class="field">
              <span class="label">Description</span>
              <textarea v-model="goalDescriptionInput" class="native-textarea" rows="3" />
            </label>

            <template v-if="!goalIsChecklist">
              <template v-if="goalDialogMode === 'create'">
                <label class="checkbox-row">
                  <input v-model="goalUseNewMetric" type="checkbox" />
                  <span>Create a new metric as part of this goal</span>
                </label>

                <template v-if="goalUseNewMetric">
                  <label class="field">
                    <span class="label">Name</span>
                    <InputText v-model="goalNewMetricNameInput" />
                  </label>

                  <label class="field">
                    <span class="label">New metric type</span>
                    <select v-model="goalNewMetricTypeInput" class="native-file-input">
                      <option value="number">Number</option>
                      <option value="count">Count</option>
                      <option value="date">Date</option>
                    </select>
                  </label>

                  <label v-if="isNumericMetricType(goalNewMetricTypeInput)" class="field">
                    <span class="label">Decimal places</span>
                    <input
                      v-model="goalNewMetricDecimalPlacesInput"
                      class="native-file-input"
                      type="number"
                      min="0"
                      max="6"
                      step="1"
                    />
                  </label>

                  <label class="field">
                    <span class="label">Unit label</span>
                    <InputText v-model="goalNewMetricUnitLabelInput" placeholder="Optional, like lbs" />
                  </label>

                  <label v-if="isNumericMetricType(goalNewMetricTypeInput)" class="field">
                    <span class="label">
                      {{ goalNewMetricTypeInput === "count" ? "Initial metric total" : "Initial metric value" }}
                    </span>
                    <input
                      v-model="goalNewMetricInitialNumberValueInput"
                      class="native-file-input"
                      type="number"
                      :step="numberInputStep(parseDecimalPlaces(goalNewMetricDecimalPlacesInput))"
                    />
                  </label>

                  <label v-else class="field">
                    <span class="label">Initial metric value</span>
                    <input v-model="goalNewMetricInitialDateValueInput" class="native-file-input" type="date" />
                  </label>
                </template>

                <label v-else class="field">
                  <span class="label">Metric</span>
                  <select v-model="goalMetricIdInput" class="native-file-input">
                    <option v-for="metric in activeMetrics" :key="metric.id" :value="metric.id">
                      {{ metric.name }} ({{ metric.metric_type }})
                    </option>
                  </select>
                </label>
              </template>
              <div v-else class="widget-dialog-note">
                Metric: {{ editingGoal?.metric?.name }} ({{ editingGoal?.metric?.metric_type }})
              </div>
            </template>

            <template v-else>
              <div class="field">
                <span class="label">Checklist items</span>
                <div class="checklist-item-row">
                  <InputText v-model="goalChecklistItemInput" placeholder="Add an item like Mop floors" />
                  <Button label="Add item" icon="pi pi-plus" severity="secondary" type="button" @click="addChecklistItem" />
                </div>
                <div v-if="goalChecklistItems.length > 0" class="checklist-item-list">
                  <button
                    v-for="(item, index) in goalChecklistItems"
                    :key="item.id ?? `${item.title}-${index}`"
                    class="exception-date-chip checklist-item-chip"
                    type="button"
                    @click="removeChecklistItem(index)"
                  >
                    <span>{{ item.title }}</span>
                    <i class="pi pi-times" />
                  </button>
                </div>
                <div v-else class="widget-dialog-note">
                  Checklist goals need at least one item.
                </div>
              </div>
            </template>

            <div class="date-grid">
              <label class="field">
                <span class="label">Start date</span>
                <input v-model="goalStartDateInput" class="native-file-input" type="date" />
              </label>

              <label class="field">
                <span class="label">Target date</span>
                <input v-model="goalTargetDateInput" class="native-file-input" type="date" />
              </label>
            </div>

            <label
              v-if="!goalIsChecklist && goalMetricType !== null && isNumericMetricType(goalMetricType)"
              class="field"
            >
              <span class="label">Target metric value</span>
              <input
                v-model="goalTargetNumberValueInput"
                class="native-file-input"
                type="number"
                :step="numberInputStep(goalMetricDecimalPlaces)"
              />
            </label>

            <template v-if="!goalIsChecklist && goalMetricType === 'date'">
              <label class="field">
                <span class="label">Success threshold percent</span>
                <input
                  v-model="goalSuccessThresholdPercentInput"
                  class="native-file-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                />
              </label>

              <div class="field">
                <span class="label">Exception dates</span>
                <div class="exception-date-row">
                  <input v-model="goalExceptionDateInput" class="native-file-input" type="date" />
                  <Button label="Add" icon="pi pi-plus" severity="secondary" type="button" @click="addGoalExceptionDate" />
                </div>
                <div v-if="goalExceptionDates.length > 0" class="exception-date-list">
                  <button
                    v-for="exceptionDate in goalExceptionDates"
                    :key="exceptionDate"
                    class="exception-date-chip"
                    type="button"
                    @click="removeGoalExceptionDate(exceptionDate)"
                  >
                    <span>{{ exceptionDate }}</span>
                    <i class="pi pi-times" />
                  </button>
                </div>
              </div>
            </template>
          </div>

          <div class="dialog-actions-row">
            <Button label="Cancel" severity="secondary" text @click="goalDialogVisible = false" />
            <Button
              :label="goalDialogMode === 'create' ? 'Create goal' : 'Save goal'"
              icon="pi pi-flag"
              :loading="goalsStore.submissionState === 'submitting'"
              @click="submitGoalForm"
            />
          </div>
        </section>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
@import "./management.css";

.date-grid {
  display: grid;
  gap: 1rem;
}

.checkbox-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  color: var(--color-text-subtle);
}

.checklist-item-row,
.exception-date-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.checklist-item-row :deep(.p-inputtext),
.exception-date-row .native-file-input {
  flex: 1 1 auto;
}

.checklist-item-list,
.exception-date-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.75rem;
}

.exception-date-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.7rem;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border-chip);
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
  cursor: pointer;
}

.exception-date-chip:hover {
  border-color: var(--color-border-chip-hover);
  color: var(--color-text-danger);
}

.goal-checklist-preview {
  display: grid;
  gap: 0.5rem;
}

.goal-checklist-preview-item {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  color: var(--color-text-subtle);
}

.goal-checklist-preview-item.completed {
  color: var(--color-text-faint);
}

.goal-checklist-preview-item.completed span {
  text-decoration: line-through;
}

@media (max-width: 720px) {
  .toolbar-filter-button :deep(.p-button-label) {
    display: none;
  }

  .checklist-item-row,
  .exception-date-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
