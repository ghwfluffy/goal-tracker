<script setup lang="ts">
import { ref } from "vue";
import Button from "primevue/button";

defineProps<{
  description: string;
  primaryActionLabel: string;
  primaryActionLoading?: boolean;
  title: string;
  viewMode: "table" | "cards";
}>();

const emit = defineEmits<{
  add: [];
  "update:viewMode": [value: "table" | "cards"];
}>();

const descriptionVisible = ref(false);
</script>

<template>
  <div class="management-toolbar panel-card">
    <div class="management-toolbar-copy">
      <div class="management-toolbar-heading">
        <div>
          <h2>{{ title }}</h2>
        </div>
        <Button
          icon="pi pi-info-circle"
          text
          rounded
          aria-label="Show section details"
          class="info-toggle"
          @click="descriptionVisible = !descriptionVisible"
        />
      </div>
      <p v-if="descriptionVisible" class="management-toolbar-description">{{ description }}</p>
    </div>

    <div class="management-toolbar-actions">
      <slot name="leading-actions" />

      <div class="view-toggle" role="group" aria-label="Change view mode">
        <button
          type="button"
          class="view-toggle-button"
          :class="{ active: viewMode === 'table' }"
          aria-label="Table view"
          @click="emit('update:viewMode', 'table')"
        >
          <span class="view-toggle-short">▦</span>
          <span class="view-toggle-full">Table</span>
        </button>
        <button
          type="button"
          class="view-toggle-button"
          :class="{ active: viewMode === 'cards' }"
          aria-label="Cards view"
          @click="emit('update:viewMode', 'cards')"
        >
          <span class="view-toggle-short">▤</span>
          <span class="view-toggle-full">Cards</span>
        </button>
      </div>

      <Button
        :label="primaryActionLabel"
        icon="pi pi-plus"
        :loading="primaryActionLoading"
        class="primary-action-button"
        @click="emit('add')"
      />
    </div>
  </div>
</template>

<style scoped>
.management-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-5);
}

.management-toolbar-copy {
  flex: 1 1 24rem;
  min-width: 0;
}

.management-toolbar-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.management-toolbar-copy h2 {
  margin: 0;
}

.management-toolbar-description {
  margin: var(--space-3) 0 0;
  line-height: var(--line-height-copy);
  color: var(--color-text-muted);
  max-width: 44rem;
}

.management-toolbar-actions,
.view-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.management-toolbar-actions {
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-left: auto;
}

.view-toggle {
  padding: 0.2rem;
  border-radius: var(--radius-pill);
  background: var(--color-surface-muted);
}

.view-toggle-button {
  min-width: 3rem;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  border-radius: var(--radius-pill);
  padding: 0.45rem 0.8rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.view-toggle-button.active {
  background: var(--color-surface-panel-strong);
  color: var(--color-text-strong);
  box-shadow: var(--shadow-sm);
}

.view-toggle-short {
  display: none;
}

.info-toggle {
  flex: 0 0 auto;
}

@media (max-width: 900px) {
  .management-toolbar,
  .management-toolbar-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .management-toolbar-actions {
    width: 100%;
    margin-left: 0;
  }

  .management-toolbar-copy {
    flex: 0 1 auto;
  }
}

@media (max-width: 720px) {
  .management-toolbar {
    gap: var(--space-4);
  }

  .management-toolbar-actions {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .view-toggle {
    gap: 0;
  }

  .view-toggle-button {
    min-width: 2.4rem;
    padding: 0.45rem 0.7rem;
  }

  .view-toggle-short {
    display: inline;
  }

  .view-toggle-full {
    display: none;
  }

  .primary-action-button {
    margin-left: auto;
  }

  .management-toolbar-copy {
    width: 100%;
  }

  .primary-action-button :deep(.p-button-label) {
    font-size: 0.9rem;
  }
}
</style>
