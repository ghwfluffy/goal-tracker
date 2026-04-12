<script setup lang="ts">
import { computed, ref } from "vue";
import type { MenuItem } from "primevue/menuitem";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import Menu from "primevue/menu";
import Tag from "primevue/tag";

import type { UserSummary } from "../../lib/api";

const props = defineProps<{
  notificationCount: number;
  user: UserSummary;
  version: string | null;
}>();

const emit = defineEmits<{
  deleteAccount: [];
  logout: [];
  openBackups: [];
  openNotifications: [];
  openInvitationCodes: [];
  openPassword: [];
  openProfile: [];
  openSharedLinks: [];
}>();

const profileMenu = ref<InstanceType<typeof Menu> | null>(null);

const currentDisplayName = computed(
  () => props.user.display_name || props.user.username,
);

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
    {
      icon: "pi pi-share-alt",
      label: "Shared links",
      command: () => emit("openSharedLinks"),
    },
  ];

  if (props.user.is_admin) {
    items.push({
      icon: "pi pi-database",
      label: "Backups",
      command: () => emit("openBackups"),
    });
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
  <header class="app-header surface-panel-soft">
    <div class="brand-block">
      <h1 class="brand-title">Goal Tracker</h1>
    </div>

    <div class="header-actions">
      <Tag v-if="version !== null" :value="`v${version}`" severity="success" />
      <Button
        class="notification-button"
        severity="secondary"
        text
        aria-label="Open notifications"
        @click="emit('openNotifications')"
      >
        <span class="notification-button-content">
          <i class="pi pi-bell" />
          <span v-if="notificationCount > 0" class="notification-badge">{{
            notificationCount
          }}</span>
        </span>
      </Button>
      <Button
        class="profile-button"
        severity="secondary"
        text
        @click="toggleProfileMenu"
      >
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
  gap: var(--space-6);
  align-items: center;
  padding: var(--space-9) var(--space-10);
}

.brand-title {
  margin: 0;
  font-size: clamp(1.9rem, 4vw, 2.8rem);
}

.brand-summary {
  margin: var(--space-4) 0 0;
  line-height: var(--line-height-copy);
  color: var(--color-text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.profile-button :deep(.p-button-label) {
  flex: 0 0 auto;
}

.notification-button-content {
  position: relative;
  display: inline-grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
}

.notification-button-content .pi {
  font-size: 1.1rem;
}

.notification-badge {
  position: absolute;
  top: -0.15rem;
  right: -0.15rem;
  min-width: 1.1rem;
  height: 1.1rem;
  padding: 0 0.2rem;
  border-radius: var(--radius-pill);
  background: var(--color-surface-panel-strong);
  color: var(--color-text-danger);
  border: 1px solid var(--color-border-danger-soft);
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.1rem;
  text-align: center;
}

.profile-button-content {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
}

.profile-name {
  font-weight: 600;
  color: var(--color-text-strong);
}

@media (max-width: 720px) {
  .app-header {
    padding: var(--space-3) var(--space-4);
    gap: var(--space-3);
    align-items: center;
  }

  .header-actions {
    justify-content: space-between;
    width: 100%;
  }

  .brand-title {
    font-size: 1.35rem;
    line-height: 1;
  }

  .profile-name {
    max-width: 7rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .profile-button-content {
    gap: var(--space-3);
  }
}
</style>
