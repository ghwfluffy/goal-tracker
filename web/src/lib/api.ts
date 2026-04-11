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
  avatar_version: string | null;
  display_name: string | null;
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

export interface RegistrationPayload extends CredentialsPayload {
  invitation_code: string;
  is_example_data: boolean;
}

export interface UpdateProfilePayload {
  display_name: string | null;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface DeleteAccountPayload {
  password: string;
}

export interface InvitationCodeUserSummary {
  created_at: string;
  display_name: string | null;
  id: string;
  is_example_data: boolean;
  username: string;
}

export interface InvitationCodeSummary {
  code: string;
  created_at: string;
  created_by_username: string | null;
  expires_at: string;
  id: string;
  revoked_at: string | null;
  users_created: InvitationCodeUserSummary[];
}

export interface InvitationCodeListResponse {
  invitation_codes: InvitationCodeSummary[];
}

export interface InvitationCodePayload {
  expires_at: string;
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

export function registerWithInvitationCode(
  payload: RegistrationPayload,
  fetcher: Fetcher = fetch,
): Promise<SessionResponse> {
  return requestJson<SessionResponse>(
    "/auth/register",
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

export function updateCurrentProfile(
  payload: UpdateProfilePayload,
  fetcher: Fetcher = fetch,
): Promise<UserSummary> {
  return requestJson<UserSummary>(
    "/users/me",
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function uploadCurrentAvatar(file: File, fetcher: Fetcher = fetch): Promise<UserSummary> {
  const formData = new FormData();
  formData.append("avatar", file);

  return requestJson<UserSummary>(
    "/users/me/avatar",
    {
      body: formData,
      method: "POST",
    },
    fetcher,
  );
}

export function changeCurrentPassword(
  payload: ChangePasswordPayload,
  fetcher: Fetcher = fetch,
): Promise<UserSummary> {
  return requestJson<UserSummary>(
    "/users/me/change-password",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function deleteCurrentAccount(
  payload: DeleteAccountPayload,
  fetcher: Fetcher = fetch,
): Promise<void> {
  return requestNoContent(
    "/users/me",
    {
      body: JSON.stringify(payload),
      method: "DELETE",
    },
    fetcher,
  );
}

export function fetchInvitationCodes(
  fetcher: Fetcher = fetch,
): Promise<InvitationCodeListResponse> {
  return requestJson<InvitationCodeListResponse>("/invitation-codes", undefined, fetcher);
}

export function createInvitationCode(
  payload: InvitationCodePayload,
  fetcher: Fetcher = fetch,
): Promise<InvitationCodeSummary> {
  return requestJson<InvitationCodeSummary>(
    "/invitation-codes",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function updateInvitationCode(
  invitationCodeId: string,
  payload: InvitationCodePayload,
  fetcher: Fetcher = fetch,
): Promise<InvitationCodeSummary> {
  return requestJson<InvitationCodeSummary>(
    `/invitation-codes/${invitationCodeId}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function deleteInvitationCode(
  invitationCodeId: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  return requestNoContent(
    `/invitation-codes/${invitationCodeId}`,
    {
      method: "DELETE",
    },
    fetcher,
  );
}
