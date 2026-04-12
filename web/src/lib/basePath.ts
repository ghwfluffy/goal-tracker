export function normalizeBasePath(value: string | null | undefined): string {
  const trimmed = (value ?? "").trim();
  if (trimmed === "" || trimmed === "/") {
    return "";
  }

  const withLeadingSlash = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return withLeadingSlash.replace(/\/+$/, "");
}

export function toViteBasePath(value: string | null | undefined): string {
  const normalized = normalizeBasePath(value);
  return normalized === "" ? "/" : `${normalized}/`;
}

export function joinBasePath(
  basePath: string | null | undefined,
  path: string,
): string {
  const normalizedBasePath = normalizeBasePath(basePath);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBasePath}${normalizedPath}`;
}

export function buildApiBaseUrl(
  basePath: string,
  explicitApiBaseUrl?: string | null,
): string {
  const trimmedExplicitApiBaseUrl = explicitApiBaseUrl?.trim();
  const resolvedBaseUrl =
    trimmedExplicitApiBaseUrl && trimmedExplicitApiBaseUrl !== ""
      ? trimmedExplicitApiBaseUrl
      : joinBasePath(basePath, "/api/v1");
  return resolvedBaseUrl.replace(/\/$/, "");
}
