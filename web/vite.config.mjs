import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { loadEnv } from "vite";

function normalizeBasePath(value) {
  const trimmed = (value ?? "").trim();
  if (trimmed === "" || trimmed === "/") {
    return "";
  }

  const withLeadingSlash = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return withLeadingSlash.replace(/\/+$/, "");
}

function toViteBasePath(value) {
  const normalized = normalizeBasePath(value);
  return normalized === "" ? "/" : `${normalized}/`;
}

function basePathCompatibilityPlugin(appBasePath) {
  return {
    name: "base-path-compatibility",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (appBasePath === "" || req.url == null) {
          next();
          return;
        }

        if (
          req.url.startsWith(appBasePath) ||
          req.url.startsWith("/api") ||
          req.url.startsWith("/__vite")
        ) {
          next();
          return;
        }

        req.url = `${appBasePath}${req.url}`;
        next();
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const appBasePath = normalizeBasePath(env.VITE_APP_BASE_PATH);
  const apiProxyTarget = env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";
  const proxy = {
    "/api": {
      target: apiProxyTarget,
      changeOrigin: true,
    },
  };

  if (appBasePath !== "") {
    proxy[`${appBasePath}/api`] = {
      target: apiProxyTarget,
      changeOrigin: true,
      rewrite: (path) => path.slice(appBasePath.length),
    };
  }

  return {
    base: toViteBasePath(appBasePath),
    cacheDir: ".vite",
    plugins: [basePathCompatibilityPlugin(appBasePath), vue()],
    server: {
      host: "0.0.0.0",
      port: 8081,
      allowedHosts: true,
      proxy,
    },
    test: {
      environment: "node",
      globals: true,
    },
  };
});
