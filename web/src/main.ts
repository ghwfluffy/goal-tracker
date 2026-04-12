import { createApp } from "vue";
import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";

import App from "./App.vue";
import { joinBasePath } from "./lib/basePath";
import router from "./router";

import "primevue/resources/themes/lara-light-blue/theme.css";
import "primevue/resources/primevue.min.css";
import "primeicons/primeicons.css";
import "./style.css";

function loadVendorScript(path: string): Promise<void> {
  if (typeof document === "undefined") {
    return Promise.resolve();
  }

  const existingScript = document.querySelector<HTMLScriptElement>(
    `script[data-vendor-script="${path}"]`,
  );
  if (existingScript !== null) {
    return new Promise((resolve, reject) => {
      if (existingScript.dataset.loaded === "true") {
        resolve();
        return;
      }
      existingScript.addEventListener("load", () => resolve(), { once: true });
      existingScript.addEventListener(
        "error",
        () => reject(new Error(`Unable to load ${path}`)),
        { once: true },
      );
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = path;
    script.async = false;
    script.dataset.vendorScript = path;
    script.addEventListener(
      "load",
      () => {
        script.dataset.loaded = "true";
        resolve();
      },
      { once: true },
    );
    script.addEventListener(
      "error",
      () => reject(new Error(`Unable to load ${path}`)),
      { once: true },
    );
    document.head.appendChild(script);
  });
}

async function bootstrap(): Promise<void> {
  try {
    await loadVendorScript(
      joinBasePath(import.meta.env.BASE_URL, "/vendor/echarts.min.js"),
    );
  } catch (error) {
    console.error(error);
  }

  const app = createApp(App);
  app.use(createPinia());
  app.use(router);
  app.use(PrimeVue);
  app.use(ToastService);
  app.mount("#app");
}

void bootstrap();
