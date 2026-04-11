<script setup lang="ts">
import { computed, onMounted } from "vue";
import Button from "primevue/button";
import Card from "primevue/card";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";

import { useStatusStore } from "../stores/status";

const statusStore = useStatusStore();

const lastCheckedLabel = computed(() => {
  if (statusStore.data === null) {
    return "Waiting for the first successful API call.";
  }

  return new Date(statusStore.data.checked_at).toLocaleString();
});

onMounted(() => {
  void statusStore.loadStatus();
});
</script>

<template>
  <main class="home-view">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Phase 0 Foundation</p>
        <h1>Goal tracking, now with a live smoke-test path.</h1>
        <p class="summary">
          The landing page calls the FastAPI backend and renders the current application
          version from <code>/api/v1/status</code>.
        </p>
        <div class="actions">
          <Button label="Refresh status" icon="pi pi-refresh" @click="statusStore.loadStatus" />
        </div>
      </div>
      <Card class="status-card">
        <template #title>Application status</template>
        <template #subtitle>Backend connectivity and version smoke test</template>
        <template #content>
          <div class="status-stack">
            <div class="status-row">
              <span class="label">State</span>
              <Tag
                v-if="statusStore.state === 'ready' && statusStore.data !== null"
                :value="statusStore.data.status"
                severity="success"
              />
              <Tag v-else-if="statusStore.state === 'error'" value="error" severity="danger" />
              <Tag v-else value="loading" severity="warning" />
            </div>

            <div class="status-row">
              <span class="label">Version</span>
              <strong>{{ statusStore.data?.version ?? "pending" }}</strong>
            </div>

            <div class="status-row">
              <span class="label">Environment</span>
              <span>{{ statusStore.data?.environment ?? "unknown" }}</span>
            </div>

            <div class="status-row">
              <span class="label">Checked</span>
              <span>{{ lastCheckedLabel }}</span>
            </div>

            <div v-if="statusStore.state === 'loading'" class="loading">
              <ProgressSpinner
                strokeWidth="5"
                style="width: 2.5rem; height: 2.5rem"
                animationDuration=".8s"
              />
              <span>Requesting status from the API.</span>
            </div>

            <p v-if="statusStore.state === 'error'" class="error">
              {{ statusStore.errorMessage }}
            </p>
          </div>
        </template>
      </Card>
    </section>
  </main>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: 3rem 1.5rem;
}

.hero {
  display: grid;
  gap: 1.5rem;
  align-items: start;
  max-width: 1100px;
  margin: 0 auto;
}

.hero-copy {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 1.5rem;
  padding: 2rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.eyebrow {
  margin: 0 0 1rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 0.95;
}

.summary {
  max-width: 48rem;
  margin: 1.25rem 0 0;
  font-size: 1.1rem;
  line-height: 1.7;
  color: #334155;
}

.actions {
  margin-top: 1.5rem;
}

.status-card {
  border-radius: 1.5rem;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.status-stack {
  display: grid;
  gap: 1rem;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.label {
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}

.loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 600;
}

code {
  padding: 0.1rem 0.35rem;
  border-radius: 0.35rem;
  background: rgba(148, 163, 184, 0.16);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.4fr 1fr;
  }
}
</style>
