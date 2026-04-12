function resolveShareUrl(publicPath: string, origin: string): URL {
  return new URL(publicPath, origin);
}

export function buildShareLinkUrl(
  publicPath: string,
  origin: string,
): string {
  return resolveShareUrl(publicPath, origin).toString();
}

export function buildCacheBustedShareLinkUrl(
  publicPath: string,
  origin: string,
  timestampSeconds: number = Math.floor(Date.now() / 1000),
): string {
  const url = resolveShareUrl(publicPath, origin);
  url.searchParams.set("t", String(timestampSeconds));
  return url.toString();
}

function fallbackCopyText(value: string): void {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();

  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) {
    throw new Error("Clipboard access failed.");
  }
}

export async function copyCacheBustedShareLink(
  publicPath: string,
  origin: string,
): Promise<string> {
  const shareUrl = buildCacheBustedShareLinkUrl(publicPath, origin);
  if (navigator.clipboard?.writeText !== undefined) {
    await navigator.clipboard.writeText(shareUrl);
    return shareUrl;
  }

  fallbackCopyText(shareUrl);
  return shareUrl;
}
