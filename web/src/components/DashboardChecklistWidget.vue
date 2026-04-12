<script setup lang="ts">
import { computed, ref } from "vue";

import type { DashboardWidgetSummary } from "../lib/api";
import { useAppToast } from "../lib/toast";
import { useDashboardsStore } from "../stores/dashboards";
import { useGoalsStore } from "../stores/goals";

const props = defineProps<{
  widget: DashboardWidgetSummary;
}>();

const goalsStore = useGoalsStore();
const dashboardsStore = useDashboardsStore();
const pendingItemId = ref("");
const { showError } = useAppToast();

const checklistGoal = computed(() => {
  if (props.widget.goal?.goal_type !== "checklist") {
    return null;
  }
  return props.widget.goal;
});

async function handleToggle(itemId: string, completed: boolean): Promise<void> {
  if (checklistGoal.value === null) {
    return;
  }

  pendingItemId.value = itemId;
  const updated = await goalsStore.setChecklistItemCompleted(checklistGoal.value.id, itemId, completed);
  if (!updated) {
    showError(goalsStore.errorMessage || "Unable to update checklist item.", "Goals");
    pendingItemId.value = "";
    return;
  }

  await dashboardsStore.loadDashboards();
  pendingItemId.value = "";
}
</script>

<template>
  <div v-if="checklistGoal !== null" class="checklist-widget">
    <div class="checklist-meta">
      <strong>{{ checklistGoal.checklist_completed_count }}/{{ checklistGoal.checklist_total_count }} done</strong>
      <span v-if="checklistGoal.target_date !== null">Target {{ checklistGoal.target_date }}</span>
    </div>

    <div v-if="checklistGoal.checklist_items.length === 0" class="empty-dashed-state checklist-empty">
      No checklist items yet.
    </div>

    <label
      v-for="item in checklistGoal.checklist_items"
      :key="item.id"
      class="checklist-item"
      :class="{ completed: item.is_completed }"
    >
      <input
        class="checklist-checkbox"
        type="checkbox"
        :checked="item.is_completed"
        :disabled="pendingItemId === item.id"
        @change="void handleToggle(item.id, ($event.target as HTMLInputElement).checked)"
      />
      <span class="checklist-title">{{ item.title }}</span>
    </label>
  </div>
  <div v-else class="empty-dashed-state checklist-empty">Checklist goal data is unavailable.</div>
</template>

<style scoped>
.checklist-widget {
  display: grid;
  gap: var(--space-3);
}

.checklist-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  color: var(--color-text-subtle);
  font-size: 0.92rem;
}

.checklist-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-2) 0;
  color: var(--color-text-strong);
}

.checklist-item.completed .checklist-title {
  color: var(--color-text-faint);
  text-decoration: line-through;
}

.checklist-checkbox {
  margin-top: 0.2rem;
}

.checklist-title {
  line-height: 1.35;
}

.checklist-empty {
  min-height: 10rem;
}
</style>
