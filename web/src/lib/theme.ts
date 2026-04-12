function readRootCssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }

  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value === "" ? fallback : value;
}

export interface ChartThemeColors {
  axisLabel: string;
  axisLine: string;
  emptyBackground: string;
  emptyBorder: string;
  emptyText: string;
  gridLine: string;
  primary: string;
  primarySoft: string;
  seriesInk: string;
  success: string;
  danger: string;
}

export function getChartThemeColors(): ChartThemeColors {
  return {
    axisLabel: readRootCssVar("--chart-axis-label", "#64748b"),
    axisLine: readRootCssVar("--chart-axis-line", "#cbd5e1"),
    emptyBackground: readRootCssVar("--color-surface-muted-soft", "rgba(248, 250, 252, 0.9)"),
    emptyBorder: readRootCssVar("--color-border-dashed", "rgba(100, 116, 139, 0.45)"),
    emptyText: readRootCssVar("--color-text-faint", "#64748b"),
    gridLine: readRootCssVar("--chart-grid-line", "#e2e8f0"),
    primary: readRootCssVar("--chart-series-primary", "#2563eb"),
    primarySoft: readRootCssVar("--chart-series-primary-soft", "rgba(37, 99, 235, 0.12)"),
    seriesInk: readRootCssVar("--chart-series-ink", "#0f172a"),
    success: readRootCssVar("--chart-series-success", "#16a34a"),
    danger: readRootCssVar("--chart-series-danger", "#dc2626"),
  };
}
