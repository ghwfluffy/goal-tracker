import { formatDateOnly, formatTimestampInBrowserTimezone } from "./time";

export type TrackableMetricType = "number" | "count" | "date";

export function isNumericMetricType(metricType: TrackableMetricType): boolean {
  return metricType === "number" || metricType === "count";
}

export function parseOptionalNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }

  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export function parseDecimalPlaces(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : Math.trunc(value);
  }

  if (value.trim() === "") {
    return null;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

export function numberInputStep(decimalPlaces: number | null): string {
  const places = Math.max(decimalPlaces ?? 0, 0);
  if (places === 0) {
    return "1";
  }
  return `0.${"0".repeat(places - 1)}1`;
}

export function formatNumberValue(value: number | null, decimalPlaces: number | null): string {
  if (value === null) {
    return "No value yet";
  }

  return value.toFixed(decimalPlaces ?? 0);
}

export function formatMetricValue(
  metricType: TrackableMetricType,
  numberValue: number | null,
  dateValue: string | null,
  decimalPlaces: number | null,
): string {
  if (isNumericMetricType(metricType)) {
    return formatNumberValue(numberValue, decimalPlaces);
  }

  return formatDateOnly(dateValue);
}

export function formatDateTime(value: string): string {
  return formatTimestampInBrowserTimezone(value);
}
