<script setup lang="ts">
import { computed } from "vue";

import type { DashboardWidgetSummary } from "../lib/api";
import {
  getDashboardWidgetPercentLabel,
  getDashboardWidgetPercentValue,
} from "../lib/dashboardWidgets";

const props = withDefaults(
  defineProps<{
    compact?: boolean;
    widget: DashboardWidgetSummary;
  }>(),
  {
    compact: false,
  },
);

const percentValue = computed(() => getDashboardWidgetPercentValue(props.widget));

const clampedPercent = computed(() => {
  const value = percentValue.value;
  if (value === null) {
    return 0;
  }
  return Math.max(0, Math.min(value, 100));
});

const displayPercent = computed(() => {
  const value = percentValue.value;
  if (value === null) {
    return "No value";
  }
  return `${Math.round(value)}%`;
});

const valueLabel = computed(() => getDashboardWidgetPercentLabel(props.widget));

const toneClass = computed(() => {
  if (props.widget.widget_type === "goal_failure_risk") {
    return "is-danger";
  }
  if (props.widget.widget_type === "goal_completion_percent") {
    return "is-primary";
  }
  return "is-success";
});
</script>

<template>
  <div class="dashboard-percent-widget" :class="[toneClass, { 'is-compact': compact }]">
    <div class="dashboard-percent-widget__topline">
      <span class="dashboard-percent-widget__label">{{ valueLabel }}</span>
      <span class="dashboard-percent-widget__value">{{ displayPercent }}</span>
    </div>
    <div
      class="dashboard-percent-widget__track"
      :aria-label="`${valueLabel} ${displayPercent}`"
      role="img"
    >
      <div class="dashboard-percent-widget__fill" :style="{ width: `${clampedPercent}%` }"></div>
      <div class="dashboard-percent-widget__marker" :style="{ left: `${clampedPercent}%` }"></div>
    </div>
    <div class="dashboard-percent-widget__scale" aria-hidden="true">
      <span>0%</span>
      <span>100%</span>
    </div>
  </div>
</template>

<style scoped>
.dashboard-percent-widget {
  --percent-start: color-mix(in srgb, var(--chart-series-primary) 78%, white 22%);
  --percent-end: color-mix(in srgb, var(--chart-series-success) 92%, white 8%);
  --percent-glow: color-mix(in srgb, var(--chart-series-success) 26%, transparent);
  --percent-marker: var(--chart-series-primary);

  display: grid;
  gap: var(--space-4);
  width: min(100%, 28rem);
}

.dashboard-percent-widget.is-primary {
  --percent-start: color-mix(in srgb, var(--chart-series-primary) 84%, white 16%);
  --percent-end: color-mix(in srgb, var(--chart-series-primary) 52%, var(--chart-series-success) 48%);
  --percent-glow: color-mix(in srgb, var(--chart-series-primary) 28%, transparent);
  --percent-marker: var(--chart-series-primary);
}

.dashboard-percent-widget.is-success {
  --percent-start: color-mix(in srgb, var(--chart-series-primary) 54%, var(--chart-series-success) 46%);
  --percent-end: var(--chart-series-success);
  --percent-glow: color-mix(in srgb, var(--chart-series-success) 30%, transparent);
  --percent-marker: var(--chart-series-primary);
}

.dashboard-percent-widget.is-danger {
  --percent-start: color-mix(in srgb, #f59e0b 74%, white 26%);
  --percent-end: color-mix(in srgb, var(--chart-series-danger) 88%, #b91c1c 12%);
  --percent-glow: color-mix(in srgb, var(--chart-series-danger) 26%, transparent);
  --percent-marker: color-mix(in srgb, var(--chart-series-danger) 75%, #f59e0b 25%);
}

.dashboard-percent-widget__topline {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
}

.dashboard-percent-widget__label {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-faint);
}

.dashboard-percent-widget__value {
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  font-weight: 800;
  letter-spacing: -0.045em;
  line-height: 0.95;
  color: var(--color-text-strong);
}

.dashboard-percent-widget__track {
  position: relative;
  height: 1.15rem;
  border-radius: var(--radius-pill);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--color-border-panel-strong) 75%, white 25%);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(226, 232, 240, 0.82)),
    linear-gradient(90deg, rgba(15, 23, 42, 0.04), rgba(148, 163, 184, 0.14));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.7),
    inset 0 -1px 0 rgba(148, 163, 184, 0.18);
}

.dashboard-percent-widget__track::before {
  content: "";
  position: absolute;
  inset: -30% auto -30% -8%;
  width: 38%;
  background: radial-gradient(circle, var(--percent-glow) 0%, transparent 72%);
  pointer-events: none;
}

.dashboard-percent-widget__fill {
  position: relative;
  height: 100%;
  min-width: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--percent-start), var(--percent-end));
  box-shadow:
    0 0 18px var(--percent-glow),
    inset 0 0 10px rgba(255, 255, 255, 0.2);
}

.dashboard-percent-widget__fill::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    120deg,
    transparent 0%,
    rgba(255, 255, 255, 0.5) 36%,
    transparent 72%
  );
  transform: translateX(-120%);
  animation: percent-shimmer 1.8s linear infinite;
  mix-blend-mode: screen;
}

.dashboard-percent-widget__marker {
  position: absolute;
  top: 50%;
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.92);
  background: var(--percent-marker);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--percent-glow) 68%, transparent),
    0 0 16px color-mix(in srgb, var(--percent-marker) 38%, transparent);
  transform: translate(-50%, -50%);
}

.dashboard-percent-widget__scale {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--color-text-faint);
}

.dashboard-percent-widget.is-compact {
  gap: var(--space-2);
  width: 100%;
}

.dashboard-percent-widget.is-compact .dashboard-percent-widget__label {
  font-size: 0.68rem;
}

.dashboard-percent-widget.is-compact .dashboard-percent-widget__value {
  font-size: clamp(1.1rem, 4vw, 1.45rem);
}

.dashboard-percent-widget.is-compact .dashboard-percent-widget__track {
  height: 0.82rem;
}

.dashboard-percent-widget.is-compact .dashboard-percent-widget__marker {
  width: 0.72rem;
  height: 0.72rem;
}

.dashboard-percent-widget.is-compact .dashboard-percent-widget__scale {
  font-size: 0.68rem;
}

@keyframes percent-shimmer {
  to {
    transform: translateX(120%);
  }
}
</style>
