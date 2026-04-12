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
  <section class="tabs-shell">
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
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(31, 41, 55, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}
</style>
