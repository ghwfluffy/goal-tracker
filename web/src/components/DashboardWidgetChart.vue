<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { getActivePinia } from "pinia";

import type { DashboardWidgetSummary } from "../lib/api";
import { getPaddedNumericAxisBounds } from "../lib/chart";
import {
  getDashboardWidgetValueText,
  isDashboardPercentWidget,
  isDashboardValueWidget,
} from "../lib/dashboardWidgets";
import {
  buildGoalForecastSeries,
  type ForecastChartPoint as ChartPoint,
} from "../lib/goalForecast";
import { getChartThemeColors } from "../lib/theme";
import { DEFAULT_PROFILE_TIMEZONE, formatDateOnly } from "../lib/time";
import { isNumericMetricType } from "../lib/tracking";
import { useAuthStore } from "../stores/auth";
import DashboardPercentWidget from "./DashboardPercentWidget.vue";

interface EChartsInstance {
  dispose(): void;
  resize(): void;
  setOption(option: object, notMerge?: boolean): void;
}

interface EChartsModule {
  init(element: HTMLElement): EChartsInstance;
}

declare global {
  interface Window {
    echarts?: EChartsModule;
  }
}

const props = defineProps<{
  widget: DashboardWidgetSummary;
}>();

const chartElement = ref<HTMLElement | null>(null);
let chart: EChartsInstance | null = null;
let resizeObserver: ResizeObserver | null = null;
const isValueWidget = computed(() => isDashboardValueWidget(props.widget.widget_type));

const profileTimezone = computed(() => {
  const pinia = getActivePinia();
  if (pinia === undefined) {
    return DEFAULT_PROFILE_TIMEZONE;
  }
  return useAuthStore(pinia).currentUser?.timezone ?? DEFAULT_PROFILE_TIMEZONE;
});

const metricChartPoints = computed<ChartPoint[]>(() => {
  return props.widget.series.map((point) => {
    if (props.widget.metric?.metric_type === "date") {
      return {
        timestamp: new Date(point.recorded_at).getTime(),
        value: point.date_value === null ? 0 : new Date(`${point.date_value}T00:00:00`).getTime(),
      };
    }

    return {
      timestamp: new Date(point.recorded_at).getTime(),
      value: point.number_value ?? 0,
    };
  });
});

const goalMetricChartPoints = computed<ChartPoint[]>(() => {
  const goalMetric = props.widget.goal?.metric;
  if (goalMetric === undefined || goalMetric === null) {
    return [];
  }

  return props.widget.series.flatMap((point) => {
    if (goalMetric.metric_type === "date") {
      if (point.date_value === null) {
        return [];
      }

      return [
        {
          timestamp: new Date(point.recorded_at).getTime(),
          value: new Date(`${point.date_value}T00:00:00Z`).getTime(),
        },
      ];
    }

    if (point.number_value === null) {
      return [];
    }

    return [
      {
        timestamp: new Date(point.recorded_at).getTime(),
        value: point.number_value,
      },
    ];
  });
});

const goalPercentChartPoints = computed<ChartPoint[]>(() => {
  return props.widget.series.map((point) => ({
    timestamp: new Date(point.recorded_at).getTime(),
    value: point.progress_percent ?? 0,
  }));
});

const goalTargetEndTimestamp = computed(() => {
  if (props.widget.goal?.target_date === null || props.widget.goal?.target_date === undefined) {
    return null;
  }
  return new Date(`${props.widget.goal.target_date}T23:59:59`).getTime();
});

const goalTargetValue = computed(() => {
  const goal = props.widget.goal;
  if (goal === null || goal === undefined) {
    return null;
  }
  if (goal.metric === null) {
    return null;
  }

  if (goal.metric.metric_type === "date") {
    return goal.target_value_date === null
      ? null
      : new Date(`${goal.target_value_date}T00:00:00Z`).getTime();
  }

  return goal.target_value_number;
});

const goalProgressUsesMetricSeries = computed(() => goalMetricChartPoints.value.length > 0);

const displayValueText = computed(() => getDashboardWidgetValueText(props.widget, profileTimezone.value));
const isPercentWidget = computed(() => isDashboardPercentWidget(props.widget.widget_type));

const hasRenderableContent = computed(() => {
  if (isValueWidget.value) {
    return displayValueText.value !== "No value";
  }
  if (props.widget.widget_type === "goal_progress") {
    return goalProgressUsesMetricSeries.value
      ? goalMetricChartPoints.value.length > 0
      : goalPercentChartPoints.value.length > 0;
  }
  return metricChartPoints.value.length > 0;
});

const metricHistoryAxisBounds = computed(() => {
  if (props.widget.metric === null || props.widget.metric === undefined) {
    return null;
  }
  if (!isNumericMetricType(props.widget.metric.metric_type)) {
    return null;
  }
  return getPaddedNumericAxisBounds(metricChartPoints.value.map((point) => point.value));
});

const goalMetricAxisBounds = computed(() => {
  if (props.widget.goal?.metric === null || props.widget.goal?.metric === undefined) {
    return null;
  }
  if (!isNumericMetricType(props.widget.goal.metric.metric_type)) {
    return null;
  }

  const values = [
    ...goalMetricChartPoints.value.map((point) => point.value),
  ];
  const targetValue = goalTargetValue.value;
  if (typeof targetValue === "number") {
    values.push(targetValue);
  }

  return getPaddedNumericAxisBounds(values);
});

function formatMetricAxisValue(value: number): string {
  if (props.widget.metric?.metric_type !== "date") {
    return value.toFixed(props.widget.metric?.decimal_places ?? 0);
  }
  return formatDateOnly(new Date(value).toISOString().slice(0, 10));
}

function formatGoalMetricAxisValue(value: number): string {
  if (props.widget.goal?.metric === null || props.widget.goal?.metric === undefined) {
    return `${Math.round(value)}%`;
  }
  if (props.widget.goal.metric.metric_type !== "date") {
    return value.toFixed(props.widget.goal.metric.decimal_places ?? 0);
  }
  return formatDateOnly(new Date(value).toISOString().slice(0, 10));
}

function createMetricHistoryOption(): object {
  const chartTheme = getChartThemeColors();
  return {
    animation: false,
    grid: { left: 14, right: 10, top: 12, bottom: 20, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: chartTheme.axisLine } },
      axisLabel: { color: chartTheme.axisLabel, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      min: metricHistoryAxisBounds.value?.min,
      max: metricHistoryAxisBounds.value?.max,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: chartTheme.gridLine } },
      axisLabel: {
        color: chartTheme.axisLabel,
        formatter: (value: number) => formatMetricAxisValue(value),
      },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: metricChartPoints.value.map((point) => [point.timestamp, point.value]),
        lineStyle: { color: chartTheme.primary, width: 3 },
        itemStyle: { color: chartTheme.primary },
      },
    ],
  };
}

function createGoalMetricProgressOption(): object {
  const chartTheme = getChartThemeColors();
  const actualPoints = goalMetricChartPoints.value.map((point) => [point.timestamp, point.value]);
  const targetValue = goalTargetValue.value;
  const nowTimestamp = Date.now();

  const forecast =
    targetValue === null
      ? { bridgeSeries: [], futureSeries: [], nowPoint: null }
      : buildGoalForecastSeries({
          actualPoints: goalMetricChartPoints.value,
          algorithm: props.widget.forecast_algorithm ?? "simple",
          nowTimestamp,
          targetValue,
        });

  return {
    animation: false,
    grid: { left: 14, right: 10, top: 12, bottom: 20, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: chartTheme.axisLine } },
      axisLabel: { color: chartTheme.axisLabel, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      min: goalMetricAxisBounds.value?.min,
      max: goalMetricAxisBounds.value?.max,
      axisLine: { show: false },
      axisLabel: {
        color: chartTheme.axisLabel,
        formatter: (value: number) => formatGoalMetricAxisValue(value),
      },
      splitLine: { lineStyle: { color: chartTheme.gridLine } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: actualPoints,
        lineStyle: { color: chartTheme.success, width: 3 },
        itemStyle: { color: chartTheme.success },
      },
      {
        type: "line",
        smooth: false,
        symbol: "none",
        data: forecast.bridgeSeries,
        tooltip: { show: false },
        lineStyle: { color: chartTheme.primary, width: 3 },
      },
      {
        type: "scatter",
        symbol: "circle",
        symbolSize: 9,
        data: forecast.nowPoint === null ? [] : [forecast.nowPoint],
        tooltip: { show: false },
        itemStyle: { color: chartTheme.primary },
      },
      {
        type: "line",
        smooth: false,
        symbol: "none",
        data: forecast.futureSeries,
        tooltip: { show: false },
        lineStyle: { color: chartTheme.danger, width: 3 },
      },
    ],
  };
}

function forecastValueAtTimestamp(
  timestamp: number,
  {
    lastActualTimestamp,
    lastActualValue,
    targetEndTimestamp,
    targetValue,
  }: {
    lastActualTimestamp: number;
    lastActualValue: number;
    targetEndTimestamp: number;
    targetValue: number;
  },
): number {
  if (targetEndTimestamp <= lastActualTimestamp) {
    return targetValue;
  }

  const progressRatio =
    (timestamp - lastActualTimestamp) / (targetEndTimestamp - lastActualTimestamp);
  const projectedValue = lastActualValue + (targetValue - lastActualValue) * progressRatio;
  const lowerBound = Math.min(lastActualValue, targetValue);
  const upperBound = Math.max(lastActualValue, targetValue);
  return Math.max(lowerBound, Math.min(projectedValue, upperBound));
}

function createGoalPercentProgressOption(): object {
  const chartTheme = getChartThemeColors();
  const actualPoints = goalPercentChartPoints.value.map((point) => [point.timestamp, point.value]);
  const lastActualPoint = goalPercentChartPoints.value.at(-1) ?? null;
  const targetEndTimestamp = goalTargetEndTimestamp.value;
  const nowTimestamp = Date.now();

  const bridgeSeries: Array<[number, number]> = [];
  const futureSeries: Array<[number, number]> = [];

  if (lastActualPoint !== null && targetEndTimestamp !== null && targetEndTimestamp > lastActualPoint.timestamp) {
    const bridgeEndTimestamp = Math.min(nowTimestamp, targetEndTimestamp);
    if (bridgeEndTimestamp > lastActualPoint.timestamp) {
      bridgeSeries.push([lastActualPoint.timestamp, lastActualPoint.value]);
      bridgeSeries.push([
        bridgeEndTimestamp,
        forecastValueAtTimestamp(bridgeEndTimestamp, {
          lastActualTimestamp: lastActualPoint.timestamp,
          lastActualValue: lastActualPoint.value,
          targetEndTimestamp,
          targetValue: 100,
        }),
      ]);
    }

    if (targetEndTimestamp > nowTimestamp) {
      const futureStartTimestamp = Math.max(nowTimestamp, lastActualPoint.timestamp);
      futureSeries.push([
        futureStartTimestamp,
        forecastValueAtTimestamp(futureStartTimestamp, {
          lastActualTimestamp: lastActualPoint.timestamp,
          lastActualValue: lastActualPoint.value,
          targetEndTimestamp,
          targetValue: 100,
        }),
      ]);
      futureSeries.push([targetEndTimestamp, 100]);
    }
  }

  return {
    animation: false,
    grid: { left: 14, right: 10, top: 12, bottom: 20, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: chartTheme.axisLine } },
      axisLabel: { color: chartTheme.axisLabel, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: chartTheme.axisLabel, formatter: "{value}%" },
      splitLine: { lineStyle: { color: chartTheme.gridLine } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: actualPoints,
        lineStyle: { color: chartTheme.success, width: 3 },
        itemStyle: { color: chartTheme.success },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: bridgeSeries,
        tooltip: { show: false },
        lineStyle: { color: chartTheme.primary, width: 3 },
      },
      {
        type: "scatter",
        symbol: "circle",
        symbolSize: 9,
        data: bridgeSeries.length === 0 ? [] : [bridgeSeries[bridgeSeries.length - 1]!],
        tooltip: { show: false },
        itemStyle: { color: chartTheme.primary },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: futureSeries,
        tooltip: { show: false },
        lineStyle: { color: chartTheme.danger, width: 3 },
      },
    ],
  };
}

function createGoalProgressOption(): object {
  if (goalProgressUsesMetricSeries.value) {
    return createGoalMetricProgressOption();
  }
  return createGoalPercentProgressOption();
}

function renderChart(): void {
  const echarts = window.echarts;
  if (echarts === undefined || chartElement.value === null || !hasRenderableContent.value || isValueWidget.value) {
    return;
  }

  if (chart === null) {
    chart = echarts.init(chartElement.value);
  }

  const option =
    props.widget.widget_type === "goal_progress"
      ? createGoalProgressOption()
      : createMetricHistoryOption();

  chart.setOption(option, true);
  chart.resize();
}

function disposeChart(): void {
  if (chart !== null) {
    chart.dispose();
    chart = null;
  }
}

function handleResize(): void {
  chart?.resize();
}

watch(
  () => props.widget,
  () => {
    if (!hasRenderableContent.value || isValueWidget.value) {
      disposeChart();
      return;
    }
    renderChart();
  },
  { deep: true },
);

onMounted(() => {
  renderChart();
  window.addEventListener("resize", handleResize);
  if (chartElement.value !== null) {
    resizeObserver = new ResizeObserver(() => {
      chart?.resize();
    });
    resizeObserver.observe(chartElement.value);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  resizeObserver?.disconnect();
  disposeChart();
});
</script>

<template>
  <div v-if="isValueWidget && hasRenderableContent" class="widget-value-shell">
    <DashboardPercentWidget v-if="isPercentWidget" :widget="widget" />
    <div v-else class="widget-value">{{ displayValueText }}</div>
  </div>
  <div v-else-if="hasRenderableContent" ref="chartElement" class="widget-chart"></div>
  <div v-else class="chart-empty-state empty-dashed-state">Not enough data yet.</div>
</template>

<style scoped>
.widget-chart,
.widget-value-shell,
.chart-empty-state {
  width: 100%;
  min-height: 13rem;
}

.widget-value-shell,
.chart-empty-state {
  display: grid;
  place-items: center;
}

.widget-value {
  font-size: clamp(2rem, 4vw, 3.15rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--color-text-strong);
  text-align: center;
}

.chart-empty-state {
  min-height: 13rem;
}
</style>
