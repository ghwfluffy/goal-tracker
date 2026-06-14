/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
  readonly VITE_APP_BASE_PATH?: string;
  readonly VITE_AGENT_BASE_URL?: string;
  readonly VITE_APARTMENT_GATE_BASE_URL?: string;
  readonly VITE_AUTH_BASE_URL?: string;
  readonly VITE_AUTH_MODE?: "local" | "oauth";
  readonly VITE_FILE_SHARE_BASE_URL?: string;
  readonly VITE_GOALS_BASE_URL?: string;
  readonly VITE_MONEY_PLANNER_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
