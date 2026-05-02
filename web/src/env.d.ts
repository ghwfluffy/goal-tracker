/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
  readonly VITE_APP_BASE_PATH?: string;
  readonly VITE_AUTH_BASE_URL?: string;
  readonly VITE_AUTH_MODE?: "local" | "oauth";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
