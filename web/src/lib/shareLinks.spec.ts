import { describe, expect, it } from "vitest";

import {
  buildCacheBustedShareLinkUrl,
  buildShareLinkUrl,
} from "./shareLinks";

describe("share link helpers", () => {
  it("builds an absolute share link url", () => {
    expect(
      buildShareLinkUrl(
        "/api/v1/shares/token-123",
        "https://goals.example.com",
      ),
    ).toBe("https://goals.example.com/api/v1/shares/token-123");
  });

  it("appends an unused cache-busting timestamp when copying links", () => {
    expect(
      buildCacheBustedShareLinkUrl(
        "/api/v1/shares/token-123",
        "https://goals.example.com",
        1760000000,
      ),
    ).toBe("https://goals.example.com/api/v1/shares/token-123?t=1760000000");
  });
});
