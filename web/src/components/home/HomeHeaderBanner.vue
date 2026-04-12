<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Menu from "primevue/menu";
import Tag from "primevue/tag";

import type { UserSummary } from "../../lib/api";

const props = defineProps<{
  user: UserSummary;
  version: string | null;
}>();

const emit = defineEmits<{
  deleteAccount: [];
  logout: [];
  openInvitationCodes: [];
  openPassword: [];
  openProfile: [];
}>();

const profileMenu = ref<InstanceType<typeof Menu> | null>(null);

const currentDisplayName = computed(() => props.user.display_name || props.user.username);

const avatarLabel = computed(() => {
  const source = currentDisplayName.value.trim();
  if (source === "") {
    return "GT";
  }

  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
});

const avatarUrl = computed(() => {
  if (props.user.avatar_version === null) {
    return null;
  }

  return `/api/v1/users/me/avatar?v=${encodeURIComponent(props.user.avatar_version)}`;
});

const profileMenuItems = computed<MenuItem[]>(() => {
  const items: MenuItem[] = [
    {
      icon: "pi pi-user-edit",
      label: "Edit profile",
      command: () => emit("openProfile"),
    },
    {
      icon: "pi pi-key",
      label: "Change password",
      command: () => emit("openPassword"),
    },
  ];

  if (props.user.is_admin) {
    items.push({
      icon: "pi pi-ticket",
      label: "Invitation codes",
      command: () => emit("openInvitationCodes"),
    });
  }

  items.push(
    {
      icon: "pi pi-trash",
      label: "Delete account",
      command: () => emit("deleteAccount"),
    },
    {
      icon: "pi pi-sign-out",
      label: "Sign out",
      command: () => emit("logout"),
    },
  );

  return items;
});

function toggleProfileMenu(event: Event): void {
  profileMenu.value?.toggle(event);
}
</script>

<template>
  <header class="app-header">
    <div class="brand-block">
      <h1 class="brand-title">Goal Tracker</h1>
      <p class="brand-summary">Track goals, dashboards, and updates from one responsive app.</p>
    </div>

    <div class="header-actions">
      <Tag v-if="version !== null" :value="`v${version}`" severity="success" />
      <Button class="profile-button" severity="secondary" text @click="toggleProfileMenu">
        <span class="profile-button-content">
          <Avatar
            :image="avatarUrl ?? undefined"
            :label="avatarUrl === null ? avatarLabel : undefined"
            shape="circle"
          />
          <span class="profile-name">{{ currentDisplayName }}</span>
        </span>
      </Button>
      <Menu ref="profileMenu" :model="profileMenuItems" popup />
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1.5rem 1.75rem;
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(31, 41, 55, 0.08);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.brand-title {
  margin: 0;
  font-size: clamp(1.9rem, 4vw, 2.8rem);
}

.brand-summary {
  margin: 0.75rem 0 0;
  line-height: 1.7;
  color: #334155;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-button :deep(.p-button-label) {
  flex: 0 0 auto;
}

.profile-button-content {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-name {
  font-weight: 600;
  color: #0f172a;
}

@media (max-width: 720px) {
  .app-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: space-between;
  }

  .profile-name {
    max-width: 10rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
