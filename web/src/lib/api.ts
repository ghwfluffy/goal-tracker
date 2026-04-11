export interface StatusResponse {
  application: string;
  checked_at: string;
  environment: string;
  status: string;
  version: string;
}

export interface BootstrapStatusResponse {
  bootstrap_required: boolean;
}

export interface UserSummary {
  id: string;
  is_admin: boolean;
  is_example_data: boolean;
  username: string;
}

export interface SessionResponse {
  user: UserSummary;
}

export interface CredentialsPayload {
  password: string;
  username: string;
}

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ValidationErrorItem {
  loc?: Array<string | number>;
  msg?: string;
}

function formatValidationError(detail: ValidationErrorItem[]): string {
  return detail
    .map((item) => {
      const locationParts = (item.loc ?? [])
        .filter((part) => part !== "body")
        .map((part) => String(part));
      const location = locationParts.length > 0 ? `${locationParts.join(".")}: ` : "";
      return `${location}${item.msg ?? "Invalid input."}`;
    })
    .join(" ");
}

function buildRequestInit(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const hasJsonBody =
    init?.body !== undefined &&
    !headers.has("Content-Type") &&
    !(init.body instanceof FormData);
  if (hasJsonBody) {
    headers.set("Content-Type", "application/json");
  }

  return {
    credentials: "same-origin",
    ...init,
    headers,
  };
}

async function parseError(response: Response): Promise<ApiError> {
  const fallbackMessage = `Request failed with ${response.status}`;

  try {
    const payload = (await response.json()) as { detail?: string | ValidationErrorItem[] };
    if (Array.isArray(payload.detail)) {
      return new ApiError(response.status, formatValidationError(payload.detail));
    }

    return new ApiError(response.status, payload.detail ?? fallbackMessage);
  } catch {
    return new ApiError(response.status, fallbackMessage);
  }
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  fetcher: Fetcher = fetch,
): Promise<T> {
  const response = await fetcher(`${apiBaseUrl}${path}`, buildRequestInit(init));

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

async function requestNoContent(
  path: string,
  init?: RequestInit,
  fetcher: Fetcher = fetch,
): Promise<void> {
  const response = await fetcher(`${apiBaseUrl}${path}`, buildRequestInit(init));

  if (!response.ok) {
    throw await parseError(response);
  }
}

export function fetchStatus(fetcher: Fetcher = fetch): Promise<StatusResponse> {
  return requestJson<StatusResponse>("/status", undefined, fetcher);
}

export function fetchBootstrapStatus(fetcher: Fetcher = fetch): Promise<BootstrapStatusResponse> {
  return requestJson<BootstrapStatusResponse>("/auth/bootstrap-status", undefined, fetcher);
}

export function fetchCurrentSession(fetcher: Fetcher = fetch): Promise<SessionResponse> {
  return requestJson<SessionResponse>("/auth/me", undefined, fetcher);
}

export function bootstrapFirstUser(
  payload: CredentialsPayload,
  fetcher: Fetcher = fetch,
): Promise<SessionResponse> {
  return requestJson<SessionResponse>(
    "/auth/bootstrap",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function loginWithPassword(
  payload: CredentialsPayload,
  fetcher: Fetcher = fetch,
): Promise<SessionResponse> {
  return requestJson<SessionResponse>(
    "/auth/login",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function logoutCurrentSession(fetcher: Fetcher = fetch): Promise<void> {
  return requestNoContent(
    "/auth/logout",
    {
      method: "POST",
    },
    fetcher,
  );
}
