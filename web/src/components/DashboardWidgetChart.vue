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

const chartData = computed(() => {
  return props.widget.series.map((point) => {
    const timestamp = new Date(point.recorded_at);
    const label = timestamp.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });

    if (props.widget.widget_type === "goal_progress" || props.widget.widget_type === "goal_summary") {
      return {
        label,
        value: point.progress_percent ?? 0,
      };
    }

    if (props.widget.metric?.metric_type === "number") {
      return {
        label,
        value: point.number_value ?? 0,
      };
    }

    return {
      label,
      value: point.date_value === null ? 0 : new Date(`${point.date_value}T00:00:00Z`).getTime(),
    };
  });
});

const hasChartData = computed(() => {
  if (props.widget.widget_type === "goal_summary") {
    return props.widget.current_progress_percent !== null;
  }

  return chartData.value.length > 0;
});

function createMetricHistoryOption(): object {
  const isDateMetric = props.widget.metric?.metric_type === "date";
  const decimalPlaces = props.widget.metric?.decimal_places ?? 0;

  return {
    animation: false,
    grid: { left: 12, right: 12, top: 18, bottom: 18, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: chartData.value.map((point) => point.label),
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { color: "#64748b", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: {
        color: "#64748b",
        formatter: (value: number) => {
          if (!isDateMetric) {
            return value.toFixed(decimalPlaces);
          }

          return formatDateOnly(new Date(value).toISOString().slice(0, 10));
        },
      },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbolSize: 7,
        data: chartData.value.map((point) => point.value),
        lineStyle: { color: "#2563eb", width: 3 },
        itemStyle: { color: "#0f172a" },
        areaStyle:
          props.widget.widget_type === "metric_summary"
            ? { color: "rgba(37, 99, 235, 0.12)" }
            : undefined,
      },
    ],
  };
}

function createGoalProgressOption(): object {
  return {
    animation: false,
    grid: { left: 12, right: 12, top: 18, bottom: 18, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: chartData.value.map((point) => point.label),
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
        symbolSize: 7,
        data: chartData.value.map((point) => point.value),
        lineStyle: { color: "#16a34a", width: 3 },
        itemStyle: { color: "#14532d" },
        areaStyle:
          props.widget.widget_type === "goal_progress"
            ? { color: "rgba(22, 163, 74, 0.12)" }
            : undefined,
      },
    ],
  };
}

function createGoalSummaryOption(): object {
  return {
    animation: false,
    series: [
      {
        type: "gauge",
        min: 0,
        max: 100,
        progress: { show: true, width: 14, itemStyle: { color: "#16a34a" } },
        axisLine: { lineStyle: { width: 14, color: [[1, "#dbeafe"]] } },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        pointer: { show: false },
        detail: {
          valueAnimation: false,
          formatter: `${Math.round(props.widget.current_progress_percent ?? 0)}%`,
          color: "#0f172a",
          fontSize: 22,
          offsetCenter: [0, "10%"],
        },
        title: {
          offsetCenter: [0, "-30%"],
          color: "#64748b",
          fontSize: 12,
        },
        data: [
          {
            value: props.widget.current_progress_percent ?? 0,
            name: props.widget.target_met ? "Target met" : "In progress",
          },
        ],
      },
    ],
  };
}

function renderChart(): void {
  const echarts = window.echarts;
  if (echarts === undefined || chartElement.value === null || !hasChartData.value) {
    return;
  }

  if (chart === null) {
    chart = echarts.init(chartElement.value);
  }

  const option =
    props.widget.widget_type === "goal_summary"
      ? createGoalSummaryOption()
      : props.widget.widget_type === "goal_progress"
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
    if (!hasChartData.value) {
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
  <div v-if="hasChartData" ref="chartElement" class="widget-chart"></div>
  <div v-else class="chart-empty-state">Not enough time-series data yet.</div>
</template>

<style scoped>
.widget-chart {
  width: 100%;
  min-height: 13rem;
}

.chart-empty-state {
  min-height: 13rem;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(100, 116, 139, 0.45);
  border-radius: 1rem;
  color: #64748b;
  background: rgba(248, 250, 252, 0.9);
  text-align: center;
  padding: 1rem;
}
</style>
