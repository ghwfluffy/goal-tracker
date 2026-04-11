<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { DashboardWidgetSummary } from "../lib/api";
import { formatDateOnly } from "../lib/time";

interface EChartsInstance {
  dispose(): void;
  resize(): void;
  setOption(option: object, notMerge?: boolean): void;
}

interface EChartsModule {
  init(element: HTMLElement): EChartsInstance;
}

interface ChartPoint {
  timestamp: number;
  value: number;
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

const valueWidgetTypes = new Set([
  "metric_summary",
  "goal_summary",
  "goal_completion_percent",
  "goal_success_percent",
  "goal_failure_risk",
]);

const isValueWidget = computed(() => valueWidgetTypes.has(props.widget.widget_type));

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
  if (goalMetric === undefined) {
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

  if (goal.metric.metric_type === "date") {
    return goal.target_value_date === null
      ? null
      : new Date(`${goal.target_value_date}T00:00:00Z`).getTime();
  }

  return goal.target_value_number;
});

const goalProgressUsesMetricSeries = computed(() => goalMetricChartPoints.value.length > 0);

const displayValueText = computed(() => {
  if (props.widget.widget_type === "metric_summary") {
    const metric = props.widget.metric;
    const latestEntry = metric?.latest_entry;
    if (metric === null || metric === undefined || latestEntry === null || latestEntry === undefined) {
      return "No value";
    }
    if (metric.metric_type === "number") {
      const numberValue = latestEntry.number_value;
      if (numberValue === null) {
        return "No value";
      }
      const formatted = numberValue.toFixed(metric.decimal_places ?? 0);
      return metric.unit_label ? `${formatted} ${metric.unit_label}` : formatted;
    }
    if (latestEntry.date_value === null) {
      return "No value";
    }
    return formatDateOnly(latestEntry.date_value);
  }

  const percentValue =
    props.widget.widget_type === "goal_completion_percent"
      ? props.widget.time_completion_percent
      : props.widget.widget_type === "goal_failure_risk"
        ? props.widget.failure_risk_percent
        : props.widget.current_progress_percent;

  if (percentValue === null) {
    return "No value";
  }
  return `${Math.round(percentValue)}%`;
});

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

function formatMetricAxisValue(value: number): string {
  if (props.widget.metric?.metric_type !== "date") {
    return value.toFixed(props.widget.metric?.decimal_places ?? 0);
  }
  return formatDateOnly(new Date(value).toISOString().slice(0, 10));
}

function formatGoalMetricAxisValue(value: number): string {
  if (props.widget.goal?.metric.metric_type !== "date") {
    return value.toFixed(props.widget.goal?.metric.decimal_places ?? 0);
  }
  return formatDateOnly(new Date(value).toISOString().slice(0, 10));
}

function createMetricHistoryOption(): object {
  return {
    animation: false,
    grid: { left: 14, right: 10, top: 12, bottom: 20, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { color: "#64748b", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: {
        color: "#64748b",
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
        lineStyle: { color: "#2563eb", width: 3 },
        itemStyle: { color: "#2563eb" },
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

function createGoalMetricProgressOption(): object {
  const actualPoints = goalMetricChartPoints.value.map((point) => [point.timestamp, point.value]);
  const lastActualPoint = goalMetricChartPoints.value.at(-1) ?? null;
  const targetEndTimestamp = goalTargetEndTimestamp.value;
  const targetValue = goalTargetValue.value;
  const nowTimestamp = Date.now();

  const bridgeSeries: Array<[number, number]> = [];
  const futureSeries: Array<[number, number]> = [];

  if (
    lastActualPoint !== null &&
    targetEndTimestamp !== null &&
    targetValue !== null &&
    targetEndTimestamp > lastActualPoint.timestamp
  ) {
    const bridgeEndTimestamp = Math.min(nowTimestamp, targetEndTimestamp);
    if (bridgeEndTimestamp > lastActualPoint.timestamp) {
      bridgeSeries.push([lastActualPoint.timestamp, lastActualPoint.value]);
      bridgeSeries.push([
        bridgeEndTimestamp,
        forecastValueAtTimestamp(bridgeEndTimestamp, {
          lastActualTimestamp: lastActualPoint.timestamp,
          lastActualValue: lastActualPoint.value,
          targetEndTimestamp,
          targetValue,
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
          targetValue,
        }),
      ]);
      futureSeries.push([targetEndTimestamp, targetValue]);
    }
  }

  return {
    animation: false,
    grid: { left: 14, right: 10, top: 12, bottom: 20, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { color: "#64748b", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisLabel: {
        color: "#64748b",
        formatter: (value: number) => formatGoalMetricAxisValue(value),
      },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: actualPoints,
        lineStyle: { color: "#16a34a", width: 3 },
        itemStyle: { color: "#16a34a" },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: bridgeSeries,
        tooltip: { show: false },
        lineStyle: { color: "#2563eb", width: 3 },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: futureSeries,
        tooltip: { show: false },
        lineStyle: { color: "#dc2626", width: 3 },
      },
    ],
  };
}

function createGoalPercentProgressOption(): object {
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
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { color: "#64748b", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: "#64748b", formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        data: actualPoints,
        lineStyle: { color: "#16a34a", width: 3 },
        itemStyle: { color: "#16a34a" },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: bridgeSeries,
        tooltip: { show: false },
        lineStyle: { color: "#2563eb", width: 3 },
      },
      {
        type: "line",
        smooth: true,
        symbol: "none",
        data: futureSeries,
        tooltip: { show: false },
        lineStyle: { color: "#dc2626", width: 3 },
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
    <div class="widget-value">{{ displayValueText }}</div>
  </div>
  <div v-else-if="hasRenderableContent" ref="chartElement" class="widget-chart"></div>
  <div v-else class="chart-empty-state">Not enough data yet.</div>
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
  color: #0f172a;
  text-align: center;
}

.chart-empty-state {
  border: 1px dashed rgba(100, 116, 139, 0.45);
  border-radius: 1rem;
  color: #64748b;
  background: rgba(248, 250, 252, 0.9);
  text-align: center;
  padding: 1rem;
}
</style>
