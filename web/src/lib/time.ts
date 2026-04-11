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
