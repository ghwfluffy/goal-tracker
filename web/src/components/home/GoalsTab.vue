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

const goalsStore = useGoalsStore();
const metricsStore = useMetricsStore();

const goalRowMenu = ref<InstanceType<typeof Menu> | null>(null);
const activeGoalMenuId = ref("");
const createDialogVisible = ref(false);
const viewMode = ref<"table" | "cards">("table");
const successMessage = ref("");

const goalTitleInput = ref("");
const goalDescriptionInput = ref("");
const goalStartDateInput = ref(new Date().toISOString().slice(0, 10));
const goalTargetDateInput = ref("");
const goalTargetNumberValueInput = ref("");
const goalSuccessThresholdPercentInput = ref("100");
const goalExceptionDateInput = ref("");
const goalExceptionDates = ref<string[]>([]);
const goalUseNewMetric = ref(false);
const goalMetricIdInput = ref("");
const goalNewMetricNameInput = ref("");
const goalNewMetricTypeInput = ref<"number" | "date">("number");
const goalNewMetricDecimalPlacesInput = ref("0");
const goalNewMetricUnitLabelInput = ref("");
const goalNewMetricInitialNumberValueInput = ref("");
const goalNewMetricInitialDateValueInput = ref("");

const activeMetrics = computed(() => metricsStore.metrics.filter((metric) => !metric.is_archived));

const selectedGoalMetric = computed(() => {
  return activeMetrics.value.find((metric) => metric.id === goalMetricIdInput.value) ?? null;
});

const selectedGoalMenuGoal = computed(() => {
  return goalsStore.goals.find((goal) => goal.id === activeGoalMenuId.value) ?? null;
});

const goalMetricType = computed(() => {
  if (goalUseNewMetric.value) {
    return goalNewMetricTypeInput.value;
  }

  return selectedGoalMetric.value?.metric_type ?? "number";
});

const goalRowMenuItems = computed<MenuItem[]>(() => {
  const goal = selectedGoalMenuGoal.value;
  if (goal === null) {
    return [];
  }

  return [
    {
      icon: "pi pi-plus-circle",
      label: "Add metric update",
      command: () => emit("openMetricEntry", goal.metric.id),
    },
    {
      icon: "pi pi-chart-line",
      label: "View metric history",
      command: () => emit("openMetricHistory", goal.metric.id),
    },
  ];
});

function resetMessages(): void {
  successMessage.value = "";
  goalsStore.errorMessage = "";
}

function resetGoalForm(): void {
  goalTitleInput.value = "";
  goalDescriptionInput.value = "";
  goalStartDateInput.value = new Date().toISOString().slice(0, 10);
  goalTargetDateInput.value = "";
  goalTargetNumberValueInput.value = "";
  goalSuccessThresholdPercentInput.value = "100";
  goalExceptionDateInput.value = "";
  goalExceptionDates.value = [];
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
  resetMessages();
  resetGoalForm();
  createDialogVisible.value = true;
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

function toggleGoalRowMenu(event: Event, goalId: string): void {
  activeGoalMenuId.value = goalId;
  goalRowMenu.value?.toggle(event);
}

function isDateGoal(goal: (typeof goalsStore.goals)[number]): boolean {
  return goal.metric.metric_type === "date";
}

function formatGoalTargetSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.metric.metric_type === "number" && goal.target_value_number !== null) {
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
    return "No progress yet";
  }
  if (isDateGoal(goal) && goal.target_met !== null) {
    return `${goal.current_progress_percent}% (${goal.target_met ? "on target" : "below target"})`;
  }
  return `${goal.current_progress_percent}%`;
}

function formatGoalLatestMetricSummary(goal: (typeof goalsStore.goals)[number]): string {
  if (goal.metric.latest_entry === null) {
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

async function submitGoalForm(): Promise<void> {
  resetMessages();
  const created = await goalsStore.createGoal({
    description: goalDescriptionInput.value.trim() === "" ? null : goalDescriptionInput.value,
    metric_id: goalUseNewMetric.value ? null : goalMetricIdInput.value || null,
    new_metric: goalUseNewMetric.value
      ? {
          decimal_places:
            goalNewMetricTypeInput.value === "number"
              ? parseDecimalPlaces(goalNewMetricDecimalPlacesInput.value)
              : null,
          initial_date_value:
            goalNewMetricTypeInput.value === "date" ? goalNewMetricInitialDateValueInput.value || null : null,
          initial_number_value:
            goalNewMetricTypeInput.value === "number"
              ? parseOptionalNumber(goalNewMetricInitialNumberValueInput.value)
              : null,
          metric_type: goalNewMetricTypeInput.value,
          name: goalNewMetricNameInput.value,
          unit_label:
            goalNewMetricUnitLabelInput.value.trim() === "" ? null : goalNewMetricUnitLabelInput.value,
        }
      : null,
    exception_dates: goalMetricType.value === "date" ? goalExceptionDates.value : [],
    start_date: goalStartDateInput.value,
    success_threshold_percent:
      goalMetricType.value === "date" ? parseOptionalNumber(goalSuccessThresholdPercentInput.value) : null,
    target_date: goalTargetDateInput.value || null,
    target_value_date: null,
    target_value_number:
      goalMetricType.value === "number" ? parseOptionalNumber(goalTargetNumberValueInput.value) : null,
    title: goalTitleInput.value,
  });

  if (!created) {
    return;
  }

  successMessage.value = "Goal created.";
  createDialogVisible.value = false;
  resetGoalForm();
  await metricsStore.loadMetrics();
}
</script>

<template>
  <div class="management-shell">
    <div class="management-toolbar panel-card">
      <div>
        <p class="panel-eyebrow">Goals</p>
        <h2>Manage goals</h2>
        <p>
          Goals use the same management pattern as other backend records: table first, cards when
          you want a looser browse view.
        </p>
      </div>
      <div class="management-toolbar-actions">
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
          label="Add goal"
          icon="pi pi-plus"
          :loading="goalsStore.submissionState === 'submitting'"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <Message v-if="successMessage !== ''" severity="success" :closable="false">
      {{ successMessage }}
    </Message>
    <Message v-if="goalsStore.errorMessage !== ''" severity="error" :closable="false">
      {{ goalsStore.errorMessage }}
    </Message>

    <div v-if="goalsStore.viewState === 'loading'" class="panel-card loading">
      <ProgressSpinner
        strokeWidth="5"
        style="width: 2rem; height: 2rem"
        animationDuration=".8s"
      />
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
            <th>Metric</th>
            <th>Start</th>
            <th>Target</th>
            <th>Progress</th>
            <th>Failure risk</th>
            <th>Status</th>
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
            <td>{{ goal.metric.name }} ({{ goal.metric.metric_type }})</td>
            <td>{{ goal.start_date }}</td>
            <td>
              <div class="table-primary-cell">
                <span>{{ formatGoalTargetSummary(goal) }}</span>
                <span v-if="goal.target_date !== null" class="table-secondary-text">
                  By {{ goal.target_date }}
                </span>
              </div>
            </td>
            <td>{{ formatGoalCurrentProgressSummary(goal) }}</td>
            <td>{{ goal.failure_risk_percent === null ? "n/a" : `${goal.failure_risk_percent}%` }}</td>
            <td>
              <Tag :value="goal.status" severity="success" />
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
            <Tag :value="goal.status" severity="success" />
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
            <strong>Metric</strong>
            <span>{{ goal.metric.name }} ({{ goal.metric.metric_type }})</span>
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
            <span>{{ goal.exception_dates.join(', ') }}</span>
          </div>
          <div class="history-row">
            <strong>Latest metric</strong>
            <span>{{ formatGoalLatestMetricSummary(goal) }}</span>
          </div>
        </div>
      </article>
    </div>

    <Menu ref="goalRowMenu" :model="goalRowMenuItems" popup />

    <Dialog
      v-model:visible="createDialogVisible"
      modal
      header="Add goal"
      class="profile-dialog"
      :style="{ width: 'min(42rem, 96vw)' }"
    >
      <div class="dialog-stack">
        <Message v-if="successMessage !== ''" severity="success" :closable="false">
          {{ successMessage }}
        </Message>
        <Message v-if="goalsStore.errorMessage !== ''" severity="error" :closable="false">
          {{ goalsStore.errorMessage }}
        </Message>

        <section class="dialog-section">
          <div class="section-heading-text">
            <h3>Create a goal</h3>
            <p>Goals reference a metric and define the time window or target you care about.</p>
          </div>

          <div class="form-stack">
            <label class="field">
              <span class="label">Goal title</span>
              <InputText v-model="goalTitleInput" />
            </label>

            <label class="field">
              <span class="label">Description</span>
              <textarea v-model="goalDescriptionInput" class="native-textarea" rows="3" />
            </label>

            <label class="checkbox-row">
              <Checkbox v-model="goalUseNewMetric" binary input-id="goal-use-new-metric" />
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
                  <option value="date">Date</option>
                </select>
              </label>

              <label v-if="goalNewMetricTypeInput === 'number'" class="field">
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
                <InputText
                  v-model="goalNewMetricUnitLabelInput"
                  placeholder="Optional, like lbs"
                />
              </label>

              <label v-if="goalNewMetricTypeInput === 'number'" class="field">
                <span class="label">Initial metric value</span>
                <input
                  v-model="goalNewMetricInitialNumberValueInput"
                  class="native-file-input"
                  type="number"
                  :step="numberInputStep(parseDecimalPlaces(goalNewMetricDecimalPlacesInput))"
                />
              </label>

              <label v-else class="field">
                <span class="label">Initial metric value</span>
                <input
                  v-model="goalNewMetricInitialDateValueInput"
                  class="native-file-input"
                  type="date"
                />
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

            <label v-if="goalMetricType === 'number'" class="field">
              <span class="label">Target metric value</span>
              <input
                v-model="goalTargetNumberValueInput"
                class="native-file-input"
                type="number"
                :step="numberInputStep(selectedGoalMetric?.decimal_places ?? parseDecimalPlaces(goalNewMetricDecimalPlacesInput))"
              />
            </label>

            <template v-else>
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
                  <input
                    v-model="goalExceptionDateInput"
                    class="native-file-input"
                    type="date"
                  />
                  <Button
                    label="Add"
                    icon="pi pi-plus"
                    severity="secondary"
                    type="button"
                    @click="addGoalExceptionDate"
                  />
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
            <Button
              label="Cancel"
              severity="secondary"
              text
              @click="createDialogVisible = false"
            />
            <Button
              label="Create goal"
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
.dialog-actions-row,
.exception-date-row {
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

.date-grid {
  display: grid;
  gap: 1rem;
}

.exception-date-row .native-file-input {
  flex: 1 1 auto;
}

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
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(248, 250, 252, 0.95);
  color: #334155;
  cursor: pointer;
}

.exception-date-chip:hover {
  border-color: rgba(239, 68, 68, 0.35);
  color: #b91c1c;
}

@media (max-width: 720px) {
  .management-toolbar,
  .tracking-card-header,
  .history-row,
  .exception-date-row {
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
