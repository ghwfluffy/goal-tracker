export const DEFAULT_PROFILE_TIMEZONE = "America/Chicago";

export function getBrowserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || DEFAULT_PROFILE_TIMEZONE;
}

export function formatTimestampInBrowserTimezone(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatDateOnly(value: string | null): string {
  if (value === null) {
    return "No value yet";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatDatePartsInTimezone(value: Date, timeZone: string): {
  day: string;
  month: string;
  year: string;
} {
  const parts = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).formatToParts(value);

  return {
    day: parts.find((part) => part.type === "day")?.value ?? "01",
    month: parts.find((part) => part.type === "month")?.value ?? "01",
    year: parts.find((part) => part.type === "year")?.value ?? "1970",
  };
}

export function getCurrentDateInTimezone(timeZone: string, value: Date = new Date()): string {
  const parts = formatDatePartsInTimezone(value, timeZone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function daysBetweenDateOnly(startDate: string, endDate: string): number {
  const startTimestamp = new Date(`${startDate}T00:00:00Z`).getTime();
  const endTimestamp = new Date(`${endDate}T00:00:00Z`).getTime();
  return Math.floor((endTimestamp - startTimestamp) / 86_400_000);
}
