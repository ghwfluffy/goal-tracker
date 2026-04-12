import { describe, expect, it } from "vitest";

import { getPaddedNumericAxisBounds } from "./chart";

describe("getPaddedNumericAxisBounds", () => {
  it("pads the range by ten percent on both sides", () => {
    expect(getPaddedNumericAxisBounds([10, 20])).toEqual({
      min: 9,
      max: 21,
    });
  });

  it("expands flat lines so they still render with vertical space", () => {
    expect(getPaddedNumericAxisBounds([20, 20])).toEqual({
      min: 18,
      max: 22,
    });
  });

  it("returns null for empty input", () => {
    expect(getPaddedNumericAxisBounds([])).toBeNull();
  });
});
