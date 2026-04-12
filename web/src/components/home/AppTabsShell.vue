<script setup lang="ts">
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";

defineProps<{
  activeIndex: number;
  tabs: Array<{
    key: string;
    label: string;
  }>;
}>();

const emit = defineEmits<{
  "update:activeIndex": [value: number];
}>();
</script>

<template>
  <section class="tabs-shell surface-panel-soft">
    <TabView
      :active-index="activeIndex"
      @update:activeIndex="(value) => emit('update:activeIndex', value)"
    >
      <TabPanel v-for="tab in tabs" :key="tab.key" :header="tab.label">
        <slot :name="tab.key" />
      </TabPanel>
    </TabView>
  </section>
</template>

<style scoped>
.tabs-shell {
  margin-top: var(--space-9);
  padding: var(--space-6);
}
</style>
