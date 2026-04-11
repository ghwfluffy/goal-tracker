<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { MetricSummary } from "../lib/api";
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
  metric: MetricSummary;
}>();

const chartElement = ref<HTMLElement | null>(null);
let chart: EChartsInstance | null = null;
let resizeObserver: ResizeObserver | null = null;

const sortedEntries = computed(() => {
  return [...props.metric.entries].sort((left, right) => {
    return new Date(left.recorded_at).getTime() - new Date(right.recorded_at).getTime();
  });
});

const chartData = computed(() => {
  return sortedEntries.value.map((entry) => {
    const timestamp = new Date(entry.recorded_at);
    const label = timestamp.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });

    if (props.metric.metric_type === "number") {
      return {
        label,
        value: entry.number_value ?? 0,
      };
    }

    return {
      label,
      value: entry.date_value === null ? 0 : new Date(`${entry.date_value}T00:00:00Z`).getTime(),
    };
  });
});

const hasChartData = computed(() => chartData.value.length > 0);

function createChartOption(): object {
  const isDateMetric = props.metric.metric_type === "date";
  const decimalPlaces = props.metric.decimal_places ?? 0;

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
        areaStyle: { color: "rgba(37, 99, 235, 0.12)" },
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

  chart.setOption(createChartOption(), true);
  chart.resize();
}

function disposeChart(): void {
  if (chart !== null) {
    chart.dispose();
    chart = null;
  }
}

watch(
  () => props.metric,
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
  if (chartElement.value !== null) {
    resizeObserver = new ResizeObserver(() => {
      chart?.resize();
    });
    resizeObserver.observe(chartElement.value);
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  disposeChart();
});
</script>

<template>
  <div v-if="hasChartData" ref="chartElement" class="metric-history-chart"></div>
  <div v-else class="metric-history-empty">No history recorded yet.</div>
</template>

<style scoped>
.metric-history-chart {
  width: 100%;
  min-height: 18rem;
}

.metric-history-empty {
  min-height: 18rem;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(100, 116, 139, 0.45);
  border-radius: 1rem;
  color: #64748b;
  background: rgba(248, 250, 252, 0.9);
  text-align: center;
}
</style>
