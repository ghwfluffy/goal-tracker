<script setup lang="ts">
import Button from "primevue/button";

defineProps<{
  description: string;
  eyebrow: string;
  primaryActionLabel: string;
  primaryActionLoading?: boolean;
  title: string;
  viewMode: "table" | "cards";
}>();

const emit = defineEmits<{
  add: [];
  "update:viewMode": [value: "table" | "cards"];
}>();
</script>

<template>
  <div class="management-toolbar panel-card">
    <div class="management-toolbar-copy">
      <p class="panel-eyebrow">{{ eyebrow }}</p>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>

    <div class="management-toolbar-actions">
      <slot name="leading-actions" />

      <div class="view-toggle">
        <Button
          label="Table"
          icon="pi pi-table"
          :severity="viewMode === 'table' ? undefined : 'secondary'"
          :outlined="viewMode !== 'table'"
          @click="emit('update:viewMode', 'table')"
        />
        <Button
          label="Cards"
          icon="pi pi-th-large"
          :severity="viewMode === 'cards' ? undefined : 'secondary'"
          :outlined="viewMode !== 'cards'"
          @click="emit('update:viewMode', 'cards')"
        />
      </div>

      <Button
        :label="primaryActionLabel"
        icon="pi pi-plus"
        :loading="primaryActionLoading"
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
  gap: var(--space-6);
}

.management-toolbar-copy {
  flex: 1 1 24rem;
  min-width: 0;
}

.management-toolbar-copy h2 {
  margin: 0;
}

.management-toolbar-copy p {
  margin: var(--space-4) 0 0;
  line-height: var(--line-height-copy);
  color: var(--color-text-muted);
}

.management-toolbar-actions,
.view-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.management-toolbar-actions {
  flex: 0 0 auto;
  flex-wrap: nowrap;
  justify-content: flex-end;
  margin-left: auto;
}

@media (max-width: 900px) {
  .management-toolbar,
  .management-toolbar-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .management-toolbar-actions {
    width: 100%;
    margin-left: 0;
  }
}

@media (max-width: 720px) {
  .view-toggle {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
