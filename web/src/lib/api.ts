export interface StatusResponse {
  application: string;
  checked_at: string;
  environment: string;
  status: string;
  version: string;
}

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

export async function fetchStatus(fetcher: Fetcher = fetch): Promise<StatusResponse> {
  const response = await fetcher(`${apiBaseUrl}/status`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Status request failed with ${response.status}`);
  }

  return (await response.json()) as StatusResponse;
}
