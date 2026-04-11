import { describe, expect, it, vi } from "vitest";

import { fetchStatus } from "./api";

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
    expect(fetcher).toHaveBeenCalledWith("/api/v1/status", {
      headers: {
        Accept: "application/json",
      },
    });
  });

  it("throws when the backend responds with an error", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 503 }));

    await expect(fetchStatus(fetcher)).rejects.toThrow("Status request failed with 503");
  });
});
