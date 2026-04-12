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
  timezone: string;
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
  timezone: string | null;
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
  users_created: InvitationCodeUserSummary[];
}

export interface InvitationCodeListResponse {
  invitation_codes: InvitationCodeSummary[];
}

export interface InvitationCodePayload {
  expires_at: string;
}

export interface MetricEntrySummary {
  date_value: string | null;
  id: string;
  number_value: number | null;
  recorded_at: string;
}

export interface MetricSummary {
  archived_at: string | null;
  decimal_places: number | null;
  entries: MetricEntrySummary[];
  id: string;
  is_archived: boolean;
  latest_entry: MetricEntrySummary | null;
  metric_type: "number" | "date";
  name: string;
  unit_label: string | null;
}

export interface MetricListResponse {
  metrics: MetricSummary[];
}

export interface CreateMetricPayload {
  decimal_places: number | null;
  initial_date_value: string | null;
  initial_number_value: number | null;
  metric_type: "number" | "date";
  name: string;
  recorded_at?: string | null;
  unit_label: string | null;
}

export interface CreateMetricEntryPayload {
  date_value: string | null;
  number_value: number | null;
  recorded_at?: string | null;
}

export interface UpdateMetricPayload {
  archived: boolean;
}

export interface GoalMetricSummary {
  decimal_places: number | null;
  id: string;
  latest_entry: MetricEntrySummary | null;
  metric_type: "number" | "date";
  name: string;
  unit_label: string | null;
}

export interface GoalSummary {
  archived_at: string | null;
  current_progress_percent: number | null;
  description: string | null;
  exception_dates: string[];
  failure_risk_percent: number | null;
  id: string;
  is_archived: boolean;
  metric: GoalMetricSummary;
  start_date: string;
  status: string;
  success_threshold_percent: number | null;
  target_date: string | null;
  target_value_date: string | null;
  target_value_number: number | null;
  target_met: boolean | null;
  time_progress_percent: number | null;
  title: string;
}

export interface GoalListResponse {
  goals: GoalSummary[];
}

export interface InlineMetricPayload extends CreateMetricPayload {}

export interface CreateGoalPayload {
  description: string | null;
  exception_dates: string[];
  metric_id: string | null;
  new_metric: InlineMetricPayload | null;
  success_threshold_percent: number | null;
  start_date: string;
  target_date: string | null;
  target_value_date: string | null;
  target_value_number: number | null;
  title: string;
}

export interface UpdateGoalPayload {
  archived: boolean;
}

export interface DashboardMetricReference {
  decimal_places: number | null;
  id: string;
  latest_entry: MetricEntrySummary | null;
  metric_type: "number" | "date";
  name: string;
  unit_label: string | null;
}

export interface DashboardGoalReference {
  exception_dates: string[];
  id: string;
  metric: DashboardMetricReference;
  success_threshold_percent: number | null;
  start_date: string;
  target_date: string | null;
  target_value_date: string | null;
  target_value_number: number | null;
  title: string;
}

export interface DashboardWidgetSeriesPoint {
  date_value: string | null;
  number_value: number | null;
  progress_percent: number | null;
  recorded_at: string;
}

export type DashboardForecastAlgorithm =
  | "simple"
  | "weighted_week_over_week"
  | "weighted_day_over_day";

export interface DashboardWidgetSummary {
  current_progress_percent: number | null;
  display_order: number;
  failure_risk_percent: number | null;
  forecast_algorithm: DashboardForecastAlgorithm | null;
  grid_h: number;
  grid_w: number;
  grid_x: number;
  grid_y: number;
  mobile_grid_h?: number;
  mobile_grid_w?: number;
  mobile_grid_x?: number;
  mobile_grid_y?: number;
  goal: DashboardGoalReference | null;
  id: string;
  metric: DashboardMetricReference | null;
  rolling_window_days: number | null;
  series: DashboardWidgetSeriesPoint[];
  target_met: boolean | null;
  time_completion_percent: number | null;
  title: string;
  widget_type:
    | "metric_history"
    | "metric_summary"
    | "days_since"
    | "goal_progress"
    | "goal_summary"
    | "goal_completion_percent"
    | "goal_success_percent"
    | "goal_failure_risk";
}

export interface DashboardSummary {
  description: string | null;
  id: string;
  is_default: boolean;
  name: string;
  widgets: DashboardWidgetSummary[];
}

export interface DashboardListResponse {
  dashboards: DashboardSummary[];
}

export interface CreateDashboardPayload {
  description: string | null;
  make_default: boolean;
  name: string;
}

export interface UpdateDashboardPayload {
  description?: string | null;
  make_default?: boolean | null;
  name?: string | null;
}

export interface CreateDashboardWidgetPayload {
  forecast_algorithm?: DashboardForecastAlgorithm | null;
  goal_id: string | null;
  grid_h?: number | null;
  grid_w?: number | null;
  grid_x?: number | null;
  grid_y?: number | null;
  metric_id: string | null;
  rolling_window_days: number | null;
  title: string;
  widget_type:
    | "metric_history"
    | "metric_summary"
    | "days_since"
    | "goal_progress"
    | "goal_summary"
    | "goal_completion_percent"
    | "goal_success_percent"
    | "goal_failure_risk";
}

export interface UpdateDashboardWidgetPayload {
  forecast_algorithm?: DashboardForecastAlgorithm | null;
  grid_h?: number | null;
  grid_w?: number | null;
  grid_x?: number | null;
  grid_y?: number | null;
  layout_mode?: "desktop" | "mobile" | null;
  rolling_window_days?: number | null;
  title?: string | null;
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

export function fetchMetrics(
  includeArchivedOrFetcher: boolean | Fetcher = false,
  fetcher: Fetcher = fetch,
): Promise<MetricListResponse> {
  const includeArchived =
    typeof includeArchivedOrFetcher === "boolean" ? includeArchivedOrFetcher : false;
  const resolvedFetcher =
    typeof includeArchivedOrFetcher === "function" ? includeArchivedOrFetcher : fetcher;
  const suffix = includeArchived ? "?include_archived=true" : "";
  return requestJson<MetricListResponse>(`/metrics${suffix}`, undefined, resolvedFetcher);
}

export function createMetric(
  payload: CreateMetricPayload,
  fetcher: Fetcher = fetch,
): Promise<MetricSummary> {
  return requestJson<MetricSummary>(
    "/metrics",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function addMetricEntry(
  metricId: string,
  payload: CreateMetricEntryPayload,
  fetcher: Fetcher = fetch,
): Promise<MetricSummary> {
  return requestJson<MetricSummary>(
    `/metrics/${metricId}/entries`,
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function updateMetric(
  metricId: string,
  payload: UpdateMetricPayload,
  fetcher: Fetcher = fetch,
): Promise<MetricSummary> {
  return requestJson<MetricSummary>(
    `/metrics/${metricId}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function deleteMetric(metricId: string, fetcher: Fetcher = fetch): Promise<void> {
  return requestNoContent(
    `/metrics/${metricId}`,
    {
      method: "DELETE",
    },
    fetcher,
  );
}

export function fetchGoals(
  includeArchivedOrFetcher: boolean | Fetcher = false,
  fetcher: Fetcher = fetch,
): Promise<GoalListResponse> {
  const includeArchived =
    typeof includeArchivedOrFetcher === "boolean" ? includeArchivedOrFetcher : false;
  const resolvedFetcher =
    typeof includeArchivedOrFetcher === "function" ? includeArchivedOrFetcher : fetcher;
  const suffix = includeArchived ? "?include_archived=true" : "";
  return requestJson<GoalListResponse>(`/goals${suffix}`, undefined, resolvedFetcher);
}

export function createGoal(
  payload: CreateGoalPayload,
  fetcher: Fetcher = fetch,
): Promise<GoalSummary> {
  return requestJson<GoalSummary>(
    "/goals",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function updateGoal(
  goalId: string,
  payload: UpdateGoalPayload,
  fetcher: Fetcher = fetch,
): Promise<GoalSummary> {
  return requestJson<GoalSummary>(
    `/goals/${goalId}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function fetchDashboards(fetcher: Fetcher = fetch): Promise<DashboardListResponse> {
  return requestJson<DashboardListResponse>("/dashboards", undefined, fetcher);
}

export function createDashboard(
  payload: CreateDashboardPayload,
  fetcher: Fetcher = fetch,
): Promise<DashboardSummary> {
  return requestJson<DashboardSummary>(
    "/dashboards",
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function updateDashboard(
  dashboardId: string,
  payload: UpdateDashboardPayload,
  fetcher: Fetcher = fetch,
): Promise<DashboardSummary> {
  return requestJson<DashboardSummary>(
    `/dashboards/${dashboardId}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function deleteDashboard(
  dashboardId: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  return requestNoContent(
    `/dashboards/${dashboardId}`,
    {
      method: "DELETE",
    },
    fetcher,
  );
}

export function createDashboardWidget(
  dashboardId: string,
  payload: CreateDashboardWidgetPayload,
  fetcher: Fetcher = fetch,
): Promise<DashboardWidgetSummary> {
  return requestJson<DashboardWidgetSummary>(
    `/dashboards/${dashboardId}/widgets`,
    {
      body: JSON.stringify(payload),
      method: "POST",
    },
    fetcher,
  );
}

export function updateDashboardWidget(
  dashboardId: string,
  widgetId: string,
  payload: UpdateDashboardWidgetPayload,
  fetcher: Fetcher = fetch,
): Promise<DashboardWidgetSummary> {
  return requestJson<DashboardWidgetSummary>(
    `/dashboards/${dashboardId}/widgets/${widgetId}`,
    {
      body: JSON.stringify(payload),
      method: "PATCH",
    },
    fetcher,
  );
}

export function deleteDashboardWidget(
  dashboardId: string,
  widgetId: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  return requestNoContent(
    `/dashboards/${dashboardId}/widgets/${widgetId}`,
    {
      method: "DELETE",
    },
    fetcher,
  );
}
