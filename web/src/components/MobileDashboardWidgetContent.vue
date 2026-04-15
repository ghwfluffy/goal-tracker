<script setup lang="ts">
import { computed } from "vue";
import { getActivePinia } from "pinia";

import type { DashboardWidgetSummary } from "../lib/api";
import {
  getDashboardWidgetValueText,
  isDashboardPercentWidget,
  isDashboardValueWidget,
} from "../lib/dashboardWidgets";
import { DEFAULT_PROFILE_TIMEZONE } from "../lib/time";
import { useAuthStore } from "../stores/auth";
import DashboardChecklistWidget from "./DashboardChecklistWidget.vue";
import DashboardGoalCalendar from "./DashboardGoalCalendar.vue";
import DashboardPercentWidget from "./DashboardPercentWidget.vue";
import DashboardWidgetChart from "./DashboardWidgetChart.vue";

const props = defineProps<{
  widget: DashboardWidgetSummary;
}>();
const emit = defineEmits<{
  openMissingUpdate: [payload: { date: string; goalId: string }];
}>();

const isValueWidget = computed(() => isDashboardValueWidget(props.widget.widget_type));

const profileTimezone = computed(() => {
  const pinia = getActivePinia();
  if (pinia === undefined) {
    return DEFAULT_PROFILE_TIMEZONE;
  }
  return useAuthStore(pinia).currentUser?.timezone ?? DEFAULT_PROFILE_TIMEZONE;
});

const displayValueText = computed(() => getDashboardWidgetValueText(props.widget, profileTimezone.value));
const hasValue = computed(() => displayValueText.value !== "No value");
const isChecklistWidget = computed(() => props.widget.widget_type === "goal_checklist");
const isPercentWidget = computed(() => isDashboardPercentWidget(props.widget.widget_type));
</script>

<template>
  <DashboardChecklistWidget v-if="isChecklistWidget" :widget="widget" />
  <DashboardGoalCalendar
    v-else-if="widget.widget_type === 'goal_calendar'"
    :widget="widget"
    @open-missing-update="emit('openMissingUpdate', $event)"
  />
  <div v-else-if="isValueWidget" class="mobile-value-widget" :class="{ 'is-empty': !hasValue }">
    <DashboardPercentWidget v-if="hasValue && isPercentWidget" :widget="widget" compact />
    <div v-else class="mobile-value-text">{{ hasValue ? displayValueText : "No value yet" }}</div>
  </div>
  <div v-else class="mobile-chart-widget">
    <DashboardWidgetChart :widget="widget" />
  </div>
</template>

<style scoped>
.mobile-value-widget {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 0;
  width: 100%;
  padding: var(--space-1) 0;
}

.mobile-value-text {
  font-size: clamp(1.35rem, 5vw, 1.9rem);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
  color: var(--color-text-strong);
}

.mobile-value-widget.is-empty .mobile-value-text {
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--color-text-faint);
}

.mobile-chart-widget {
  min-height: 16rem;
}
</style>
