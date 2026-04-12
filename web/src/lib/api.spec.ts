import { describe, expect, it, vi } from "vitest";

import {
  ApiError,
  addMetricEntry,
  createDashboard,
  createDashboardWidget,
  createGoal,
  createInvitationCode,
  createMetric,
  deleteDashboard,
  deleteDashboardWidget,
  deleteInvitationCode,
  fetchBootstrapStatus,
  fetchCurrentSession,
  fetchDashboards,
  fetchGoals,
  fetchInvitationCodes,
  fetchMetrics,
  fetchStatus,
  loginWithPassword,
  registerWithInvitationCode,
  updateDashboard,
  updateDashboardWidget,
  updateInvitationCode,
} from "./api";

function headersToObject(headers: Headers): Record<string, string> {
  return Object.fromEntries(headers.entries());
}

describe("fetchStatus", () => {
  it("parses the backend status response", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          application: "Goal Tracker",
          checked_at: "2026-04-11T18:00:00Z",
          environment: "development",
          status: "ok",
          version: "0.1.0",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    });

    await expect(fetchStatus(fetcher)).resolves.toEqual({
      application: "Goal Tracker",
      checked_at: "2026-04-11T18:00:00Z",
      environment: "development",
      status: "ok",
      version: "0.1.0",
    });
    const [, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(init.credentials).toBe("same-origin");
    expect(headersToObject(init.headers as Headers)).toEqual({
      accept: "application/json",
    });
  });

  it("throws when the backend responds with an error", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 503 }));

    await expect(fetchStatus(fetcher)).rejects.toThrow("Request failed with 503");
  });
});

describe("auth api helpers", () => {
  it("requests bootstrap status with credentials", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(JSON.stringify({ bootstrap_required: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      });
    });

    await expect(fetchBootstrapStatus(fetcher)).resolves.toEqual({ bootstrap_required: true });
    const [, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(init.credentials).toBe("same-origin");
    expect(headersToObject(init.headers as Headers)).toEqual({
      accept: "application/json",
    });
  });

  it("sends login payload as json", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          user: {
            avatar_version: null,
            display_name: null,
            id: "user-1",
            is_admin: true,
            is_example_data: false,
            timezone: "America/Chicago",
            username: "admin",
          },
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    });

    await expect(
      loginWithPassword({ username: "admin", password: "supersafepassword" }, fetcher),
    ).resolves.toEqual({
      user: {
        avatar_version: null,
        display_name: null,
        id: "user-1",
        is_admin: true,
        is_example_data: false,
        timezone: "America/Chicago",
        username: "admin",
      },
    });

    const [, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(init.body).toBe(JSON.stringify({ username: "admin", password: "supersafepassword" }));
    expect(init.credentials).toBe("same-origin");
    expect(init.method).toBe("POST");
    expect(headersToObject(init.headers as Headers)).toEqual({
      accept: "application/json",
      "content-type": "application/json",
    });
  });

  it("sends registration payload as json", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          user: {
            avatar_version: null,
            display_name: null,
            id: "user-2",
            is_admin: false,
            is_example_data: true,
            timezone: "America/Chicago",
            username: "member",
          },
        }),
        {
          status: 201,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    });

    await expect(
      registerWithInvitationCode(
        {
          invitation_code: "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
          is_example_data: true,
          password: "supersafepassword",
          username: "member",
        },
        fetcher,
      ),
    ).resolves.toEqual({
      user: {
        avatar_version: null,
        display_name: null,
        id: "user-2",
        is_admin: false,
        is_example_data: true,
        timezone: "America/Chicago",
        username: "member",
      },
    });

    const [, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(
      JSON.stringify({
        invitation_code: "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
        is_example_data: true,
        password: "supersafepassword",
        username: "member",
      }),
    );
    expect(init.method).toBe("POST");
  });

  it("preserves api error details for auth requests", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(JSON.stringify({ detail: "Not authenticated." }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
        },
      });
    });

    await expect(fetchCurrentSession(fetcher)).rejects.toMatchObject({
      message: "Not authenticated.",
      name: "ApiError",
      status: 401,
    });
  });

  it("formats validation errors into readable text", async () => {
    const fetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          detail: [
            {
              type: "string_too_short",
              loc: ["body", "password"],
              msg: "String should have at least 8 characters",
            },
          ],
        }),
        {
          status: 422,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    });

    await expect(
      loginWithPassword({ username: "admin", password: "short" }, fetcher),
    ).rejects.toMatchObject({
      message: "password: String should have at least 8 characters",
      name: "ApiError",
      status: 422,
    });
  });

  it("supports invitation code admin helpers", async () => {
    const fetcher = vi.fn(async (input, init) => {
      const path = String(input);

      if (path.endsWith("/invitation-codes") && init?.method === undefined) {
        return new Response(
          JSON.stringify({
            invitation_codes: [
              {
                code: "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
                created_at: "2026-04-11T20:00:00Z",
                created_by_username: "admin",
                expires_at: "2026-04-18T20:00:00Z",
                id: "code-1",
                users_created: [],
              },
            ],
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        );
      }

      if (path.endsWith("/invitation-codes") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            code: "Z1Y2X3W4V5U6T7S8R9Q0P1O2N3M4L5K6",
            created_at: "2026-04-11T20:00:00Z",
            created_by_username: "admin",
            expires_at: "2026-04-18T20:00:00Z",
            id: "code-2",
            users_created: [],
          }),
          {
            status: 201,
            headers: {
              "Content-Type": "application/json",
            },
          },
        );
      }

      if (path.endsWith("/invitation-codes/code-1") && init?.method === "PATCH") {
        return new Response(
          JSON.stringify({
            code: "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
            created_at: "2026-04-11T20:00:00Z",
            created_by_username: "admin",
            expires_at: "2026-04-19T20:00:00Z",
            id: "code-1",
            users_created: [],
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        );
      }

      return new Response(null, { status: 204 });
    });

    await expect(fetchInvitationCodes(fetcher)).resolves.toEqual({
      invitation_codes: [
        {
          code: "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6",
          created_at: "2026-04-11T20:00:00Z",
          created_by_username: "admin",
          expires_at: "2026-04-18T20:00:00Z",
          id: "code-1",
          users_created: [],
        },
      ],
    });

    await expect(
      createInvitationCode({ expires_at: "2026-04-18T20:00:00Z" }, fetcher),
    ).resolves.toMatchObject({
      id: "code-2",
    });

    await expect(
      updateInvitationCode("code-1", { expires_at: "2026-04-19T20:00:00Z" }, fetcher),
    ).resolves.toMatchObject({
      expires_at: "2026-04-19T20:00:00Z",
    });

    await expect(deleteInvitationCode("code-1", fetcher)).resolves.toBeUndefined();
  });

  it("supports metric and goal helpers", async () => {
    const fetcher = vi.fn(async (input, init) => {
      const path = String(input);

      if (path.endsWith("/metrics") && init?.method === undefined) {
        return new Response(
          JSON.stringify({
            metrics: [
              {
                decimal_places: 1,
                entries: [],
                id: "metric-1",
                latest_entry: null,
                metric_type: "number",
                name: "Weight",
                unit_label: "lbs",
              },
            ],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/metrics") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            entries: [],
            id: "metric-2",
            latest_entry: null,
            metric_type: "date",
            name: "Last drink",
            unit_label: null,
          }),
          {
            status: 201,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/metrics/metric-1/entries") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            entries: [
              {
                date_value: null,
                id: "entry-1",
                number_value: 242.3,
                recorded_at: "2026-04-11T20:30:00Z",
              },
            ],
            decimal_places: 1,
            id: "metric-1",
            latest_entry: {
              date_value: null,
              id: "entry-1",
              number_value: 242.3,
              recorded_at: "2026-04-11T20:30:00Z",
            },
            metric_type: "number",
            name: "Weight",
            unit_label: "lbs",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/goals") && init?.method === undefined) {
        return new Response(
          JSON.stringify({
            goals: [],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      return new Response(
        JSON.stringify({
          current_progress_percent: null,
          description: "Cut steadily.",
          exception_dates: [],
          failure_risk_percent: null,
          id: "goal-1",
          metric: {
            decimal_places: 1,
            id: "metric-1",
            latest_entry: null,
            metric_type: "number",
            name: "Weight",
            unit_label: "lbs",
          },
          start_date: "2026-04-11",
          status: "active",
          success_threshold_percent: null,
          target_date: "2026-06-30",
          target_value_date: null,
          target_value_number: 220.5,
          target_met: null,
          time_progress_percent: null,
          title: "Reach 220",
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      );
    });

    await expect(fetchMetrics(fetcher)).resolves.toEqual({
      metrics: [
        {
          decimal_places: 1,
          entries: [],
          id: "metric-1",
          latest_entry: null,
          metric_type: "number",
          name: "Weight",
          unit_label: "lbs",
        },
      ],
    });

    await expect(
      createMetric(
        {
          decimal_places: 1,
          initial_date_value: null,
          initial_number_value: 245.5,
          metric_type: "number",
          name: "Weight",
          unit_label: "lbs",
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      id: "metric-2",
    });

    await expect(
      addMetricEntry(
        "metric-1",
        { date_value: null, number_value: 242.3 },
        fetcher,
      ),
    ).resolves.toMatchObject({
      latest_entry: { number_value: 242.3 },
    });

    await expect(fetchGoals(fetcher)).resolves.toEqual({ goals: [] });

    await expect(
      createGoal(
        {
          description: "Cut steadily.",
          exception_dates: [],
          metric_id: "metric-1",
          new_metric: null,
          success_threshold_percent: null,
          start_date: "2026-04-11",
          target_date: "2026-06-30",
          target_value_date: null,
          target_value_number: 220.5,
          title: "Reach 220",
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      id: "goal-1",
      title: "Reach 220",
    });
  });

  it("supports dashboard helpers", async () => {
    const fetcher = vi.fn(async (input, init) => {
      const path = String(input);

      if (path.endsWith("/dashboards") && init?.method === undefined) {
        return new Response(
          JSON.stringify({
            dashboards: [
              {
                description: "Default dashboard",
                id: "dashboard-1",
                is_default: true,
                name: "Main",
                widgets: [],
              },
            ],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/dashboards") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            description: null,
            id: "dashboard-2",
            is_default: false,
            name: "Health",
            widgets: [],
          }),
          {
            status: 201,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/dashboards/dashboard-1") && init?.method === "PATCH") {
        return new Response(
          JSON.stringify({
            description: "Updated",
            id: "dashboard-1",
            is_default: true,
            name: "Main",
            widgets: [],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/dashboards/dashboard-1/widgets") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            current_progress_percent: null,
            display_order: 1,
            failure_risk_percent: null,
            forecast_algorithm: null,
            grid_h: 4,
            grid_w: 6,
            grid_x: 0,
            grid_y: 0,
            goal: null,
            id: "widget-1",
            metric: {
              decimal_places: 1,
              id: "metric-1",
              latest_entry: null,
              metric_type: "number",
              name: "Weight",
              unit_label: "lbs",
            },
            rolling_window_days: 30,
            series: [],
            target_met: null,
            time_completion_percent: null,
            title: "Weight trend",
            widget_type: "metric_history",
          }),
          {
            status: 201,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      if (path.endsWith("/dashboards/dashboard-1/widgets/widget-1") && init?.method === "PATCH") {
        return new Response(
          JSON.stringify({
            current_progress_percent: null,
            display_order: 1,
            failure_risk_percent: null,
            forecast_algorithm: null,
            grid_h: 5,
            grid_w: 12,
            grid_x: 0,
            grid_y: 4,
            goal: null,
            id: "widget-1",
            metric: {
              decimal_places: 1,
              id: "metric-1",
              latest_entry: null,
              metric_type: "number",
              name: "Weight",
              unit_label: "lbs",
            },
            rolling_window_days: 90,
            series: [],
            target_met: null,
            time_completion_percent: null,
            title: "Weight trend",
            widget_type: "metric_history",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }

      return new Response(null, { status: 204 });
    });

    await expect(fetchDashboards(fetcher)).resolves.toEqual({
      dashboards: [
        {
          description: "Default dashboard",
          id: "dashboard-1",
          is_default: true,
          name: "Main",
          widgets: [],
        },
      ],
    });

    await expect(
      createDashboard(
        {
          description: null,
          make_default: false,
          name: "Health",
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      id: "dashboard-2",
    });

    await expect(
      updateDashboard(
        "dashboard-1",
        {
          description: "Updated",
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      description: "Updated",
    });

    await expect(
      createDashboardWidget(
        "dashboard-1",
        {
          grid_h: 4,
          grid_w: 6,
          grid_x: 0,
          grid_y: 0,
          goal_id: null,
          metric_id: "metric-1",
          rolling_window_days: 30,
          title: "Weight trend",
          widget_type: "metric_history",
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      id: "widget-1",
    });

    await expect(
      updateDashboardWidget(
        "dashboard-1",
        "widget-1",
        {
          grid_h: 5,
          grid_w: 12,
          grid_x: 0,
          grid_y: 4,
          rolling_window_days: 90,
        },
        fetcher,
      ),
    ).resolves.toMatchObject({
      rolling_window_days: 90,
    });

    await expect(deleteDashboard("dashboard-1", fetcher)).resolves.toBeUndefined();
    await expect(deleteDashboardWidget("dashboard-1", "widget-1", fetcher)).resolves.toBeUndefined();
  });
});
