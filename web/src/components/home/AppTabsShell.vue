<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Dropdown from "primevue/dropdown";
import TabPanel from "primevue/tabpanel";
import TabView from "primevue/tabview";

const MOBILE_TABS_BREAKPOINT = "(max-width: 760px)";

const props = defineProps<{
  activeIndex: number;
  tabs: Array<{
    key: string;
    label: string;
  }>;
}>();

const emit = defineEmits<{
  "update:activeIndex": [value: number];
}>();

const useCompactTabs = ref(false);
let mobileTabsMediaQuery: MediaQueryList | null = null;

const selectedTabKey = computed({
  get: () => props.tabs[props.activeIndex]?.key ?? props.tabs[0]?.key ?? "",
  set: (value: string) => {
    const nextIndex = props.tabs.findIndex((tab) => tab.key === value);
    if (nextIndex >= 0) {
      emit("update:activeIndex", nextIndex);
    }
  },
});

function syncCompactTabs(mediaQuery: MediaQueryList | MediaQueryListEvent): void {
  useCompactTabs.value = mediaQuery.matches;
}

onMounted(() => {
  mobileTabsMediaQuery = window.matchMedia(MOBILE_TABS_BREAKPOINT);
  syncCompactTabs(mobileTabsMediaQuery);
  mobileTabsMediaQuery.addEventListener("change", syncCompactTabs);
});

onBeforeUnmount(() => {
  mobileTabsMediaQuery?.removeEventListener("change", syncCompactTabs);
});
</script>

<template>
  <section class="tabs-shell surface-panel-soft">
    <div v-if="useCompactTabs" class="compact-tabs-shell">
      <Dropdown
        id="home-tab-select"
        v-model="selectedTabKey"
        :options="tabs"
        option-label="label"
        option-value="key"
        class="compact-tabs-dropdown"
      />
      <div class="compact-tabs-panel">
        <slot :name="selectedTabKey" />
      </div>
    </div>

    <TabView
      v-else
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

.compact-tabs-shell {
  display: grid;
  gap: var(--space-3);
}

.compact-tabs-dropdown {
  width: 100%;
}

@media (max-width: 720px) {
  .tabs-shell {
    margin-top: var(--space-3);
    padding: var(--space-3);
  }
}
</style>
