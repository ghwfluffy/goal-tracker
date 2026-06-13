import { describe, expect, it } from "vitest";

import { parseRollingWindowDays } from "./rollingWindow";

describe("parseRollingWindowDays", () => {
  it("parses blank string input as no rolling window", () => {
    expect(parseRollingWindowDays("")).toBeNull();
    expect(parseRollingWindowDays("   ")).toBeNull();
  });

  it("parses numeric string input as an integer", () => {
    expect(parseRollingWindowDays("30")).toBe(30);
  });

  it("accepts numeric input without string trimming", () => {
    expect(parseRollingWindowDays(30)).toBe(30);
  });

  it("ignores non-finite numeric input", () => {
    expect(parseRollingWindowDays(Number.NaN)).toBeNull();
    expect(parseRollingWindowDays(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
