import { describe, expect, it } from "vitest";

import {
  buildApiBaseUrl,
  joinBasePath,
  normalizeBasePath,
  toViteBasePath,
} from "./basePath";

describe("base path helpers", () => {
  it("normalizes optional app base paths", () => {
    expect(normalizeBasePath(undefined)).toBe("");
    expect(normalizeBasePath("")).toBe("");
    expect(normalizeBasePath("/")).toBe("");
    expect(normalizeBasePath("goals")).toBe("/goals");
    expect(normalizeBasePath("/goals/")).toBe("/goals");
  });

  it("builds vite-compatible base paths", () => {
    expect(toViteBasePath(undefined)).toBe("/");
    expect(toViteBasePath("/")).toBe("/");
    expect(toViteBasePath("/goals")).toBe("/goals/");
  });

  it("joins app-relative paths", () => {
    expect(joinBasePath("/", "/logo-large.png")).toBe("/logo-large.png");
    expect(joinBasePath("/goals/", "/logo-large.png")).toBe(
      "/goals/logo-large.png",
    );
    expect(joinBasePath("/goals", "api/v1")).toBe("/goals/api/v1");
  });

  it("derives the default api base url from the app base path", () => {
    expect(buildApiBaseUrl("/", undefined)).toBe("/api/v1");
    expect(buildApiBaseUrl("/goals/", undefined)).toBe("/goals/api/v1");
    expect(buildApiBaseUrl("/goals/", "https://api.example.com/v1/")).toBe(
      "https://api.example.com/v1",
    );
  });
});
