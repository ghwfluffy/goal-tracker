<script setup lang="ts">
import { computed, ref } from "vue";
import Dialog from "primevue/dialog";

import type { DashboardCalendarDaySummary, DashboardWidgetSummary } from "../lib/api";

const props = defineProps<{
  widget: DashboardWidgetSummary;
}>();
const emit = defineEmits<{
  openMissingUpdate: [payload: { date: string; goalId: string }];
}>();

const calendar = computed(() => props.widget.calendar);

const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const goalScopeLabel = computed(() => {
  if (calendar.value === null) {
    return "";
  }
  return calendar.value.goal_scope === "all" ? "All active goals" : `${calendar.value.goal_count} goals`;
});

const periodLabel = computed(() => {
  if (calendar.value === null) {
    return "";
  }
  if (calendar.value.period === "goal_length") {
    return "Goal length";
  }
  if (calendar.value.period === "current_month") {
    return "Current month";
  }
  return "Rolling 4 weeks";
});

const selectedDay = ref<DashboardCalendarDaySummary | null>(null);
const dayDetailsVisible = ref(false);

const selectedDayLabel = computed(() => {
  if (selectedDay.value === null) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
    weekday: "long",
    year: "numeric",
  }).format(new Date(`${selectedDay.value.date}T00:00:00Z`));
});

function dayNumber(day: DashboardCalendarDaySummary): string {
  return String(new Date(`${day.date}T00:00:00Z`).getUTCDate());
}

function isDayClickable(day: DashboardCalendarDaySummary): boolean {
  return day.goal_statuses.length > 0;
}

function markerText(day: DashboardCalendarDaySummary): string {
  if (day.status === "blank") {
    return "";
  }
  return "×";
}

function openDayDetails(day: DashboardCalendarDaySummary): void {
  if (!isDayClickable(day)) {
    return;
  }

  selectedDay.value = day;
  dayDetailsVisible.value = true;
}

function openMissingUpdate(date: string, goalId: string): void {
  dayDetailsVisible.value = false;
  emit("openMissingUpdate", { date, goalId });
}
</script>

<template>
  <div v-if="calendar !== null" class="goal-calendar-shell">
    <div class="goal-calendar-meta">
      <span>{{ periodLabel }}</span>
      <span>{{ goalScopeLabel }}</span>
    </div>

    <div class="goal-calendar-weekdays">
      <span v-for="weekday in weekdayLabels" :key="weekday">{{ weekday }}</span>
    </div>

    <div class="goal-calendar-grid">
      <div
        v-for="day in calendar.days"
        :key="day.date"
        class="goal-calendar-cell"
        :class="[`status-${day.status}`, { 'is-outside-range': !day.is_in_range }]"
      >
        <button
          v-if="isDayClickable(day)"
          type="button"
          class="goal-calendar-cell-button"
          :aria-label="`Show details for ${day.date}`"
          @click="openDayDetails(day)"
        >
          <span class="goal-calendar-day-number">{{ dayNumber(day) }}</span>
          <span class="goal-calendar-marker">{{ markerText(day) }}</span>
        </button>
        <div v-else class="goal-calendar-cell-static">
          <span class="goal-calendar-day-number">{{ dayNumber(day) }}</span>
          <span class="goal-calendar-marker">{{ markerText(day) }}</span>
        </div>
      </div>
    </div>

    <div class="goal-calendar-legend">
      <span class="legend-item status-success">Green × met</span>
      <span class="legend-item status-pending">Blue × missing</span>
      <span class="legend-item status-failed">Red × failed</span>
      <span class="legend-item status-warning">Yellow × exception</span>
    </div>

    <Dialog
      v-model:visible="dayDetailsVisible"
      modal
      :header="selectedDayLabel"
      class="goal-calendar-dialog"
      :style="{ width: 'min(30rem, calc(100vw - 2rem))' }"
    >
      <div v-if="selectedDay !== null" class="goal-calendar-detail-list">
        <div
          v-for="goalStatus in selectedDay.goal_statuses"
          :key="goalStatus.goal_id"
          class="goal-calendar-detail-row"
        >
          <span class="goal-calendar-detail-subject">{{ goalStatus.subject }}</span>
          <span class="goal-calendar-detail-separator">:</span>
          <button
            v-if="goalStatus.result_label === 'Missing'"
            type="button"
            class="goal-calendar-detail-result goal-calendar-detail-action"
            :class="`status-${goalStatus.status}`"
            @click="openMissingUpdate(selectedDay.date, goalStatus.goal_id)"
          >
            {{ goalStatus.result_label }}
          </button>
          <span v-else class="goal-calendar-detail-result" :class="`status-${goalStatus.status}`">
            {{ goalStatus.result_label }}
          </span>
        </div>
      </div>
    </Dialog>
  </div>
  <div v-else class="chart-empty-state empty-dashed-state">Calendar data is not available.</div>
</template>

<style scoped>
.goal-calendar-shell {
  display: grid;
  gap: var(--space-4);
  min-height: 16rem;
}

.goal-calendar-meta,
.goal-calendar-weekdays,
.goal-calendar-grid,
.goal-calendar-legend {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.45rem;
}

.goal-calendar-meta {
  grid-template-columns: repeat(2, minmax(0, max-content));
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  color: var(--color-text-faint);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.goal-calendar-weekdays span {
  text-align: center;
  color: var(--color-text-faint);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.goal-calendar-grid {
  align-items: stretch;
}

.goal-calendar-cell {
  min-height: 4.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-panel);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(248, 250, 252, 0.92)),
    var(--color-surface-panel-soft);
  display: grid;
  align-content: space-between;
  justify-items: center;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.goal-calendar-cell-button,
.goal-calendar-cell-static {
  width: 100%;
  min-height: 4.5rem;
  padding: 0.6rem 0.55rem;
  border: 0;
  border-radius: inherit;
  background: transparent;
  display: grid;
  align-content: space-between;
  justify-items: center;
}

.goal-calendar-cell-button {
  cursor: pointer;
  transition:
    transform 140ms ease,
    background-color 140ms ease;
}

.goal-calendar-cell-button:hover,
.goal-calendar-cell-button:focus-visible {
  background: rgba(15, 23, 42, 0.05);
  transform: translateY(-1px);
  outline: none;
}

.goal-calendar-cell.is-outside-range {
  opacity: 0.5;
}

.goal-calendar-day-number {
  color: var(--color-text-subtle);
  font-size: 0.82rem;
  font-weight: 700;
}

.goal-calendar-marker {
  min-height: 1.85rem;
  font-size: 1.9rem;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.08em;
  color: transparent;
}

.goal-calendar-cell.status-success .goal-calendar-marker,
.legend-item.status-success {
  color: var(--chart-series-success);
}

.goal-calendar-cell.status-pending .goal-calendar-marker,
.legend-item.status-pending {
  color: var(--chart-series-primary);
}

.goal-calendar-cell.status-failed .goal-calendar-marker,
.legend-item.status-failed {
  color: var(--chart-series-danger);
}

.goal-calendar-cell.status-warning .goal-calendar-marker,
.legend-item.status-warning {
  color: #d97706;
}

.goal-calendar-legend {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  color: var(--color-text-faint);
  font-size: 0.74rem;
  font-weight: 600;
}

.goal-calendar-detail-list {
  display: grid;
  gap: var(--space-3);
}

.goal-calendar-detail-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, auto);
  align-items: baseline;
  gap: 0.5rem;
  font-size: 0.98rem;
}

.goal-calendar-detail-subject {
  color: var(--color-text-strong);
  font-weight: 700;
}

.goal-calendar-detail-separator {
  color: var(--color-text-faint);
}

.goal-calendar-detail-result {
  font-weight: 700;
}

.goal-calendar-detail-action {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.goal-calendar-detail-action:hover,
.goal-calendar-detail-action:focus-visible {
  text-decoration: underline;
  outline: none;
}

.goal-calendar-detail-result.status-success {
  color: var(--chart-series-success);
}

.goal-calendar-detail-result.status-pending {
  color: var(--chart-series-primary);
}

.goal-calendar-detail-result.status-failed {
  color: var(--chart-series-danger);
}

.goal-calendar-detail-result.status-warning {
  color: #d97706;
}

.legend-item {
  text-align: center;
}

@media (max-width: 720px) {
  .goal-calendar-cell {
    min-height: 3.2rem;
  }

  .goal-calendar-cell-button,
  .goal-calendar-cell-static {
    min-height: 3.2rem;
    padding: 0.28rem 0.18rem 0.22rem;
  }

  .goal-calendar-day-number {
    font-size: 0.72rem;
  }

  .goal-calendar-marker {
    min-height: 1.2rem;
    font-size: 1.28rem;
  }

  .goal-calendar-legend {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2);
  }
}
</style>
