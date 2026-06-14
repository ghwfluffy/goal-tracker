<script setup lang="ts">
import {
  FederatedBanner,
  accountSettingsUrl,
  createGhwizFederatedSites,
  type FederatedBannerMenuItem,
  type FederatedBannerUser,
} from "@ghwiz/federated-banner";
import { computed } from "vue";

import { authMode, centralAuthBaseUrl, type UserSummary } from "../../lib/api";
import { buildApiBaseUrl, joinBasePath } from "../../lib/basePath";

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

const appUrl = joinBasePath(import.meta.env.BASE_URL, "/");
const avatarApiBaseUrl = buildApiBaseUrl(
  import.meta.env.BASE_URL,
  import.meta.env.VITE_API_BASE_URL,
);
const usesCentralAuth = authMode === "oauth";

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
    if (props.user.avatar_url !== null) {
      return props.user.avatar_url;
    }
    return null;
  }

  return `${avatarApiBaseUrl}/users/me/avatar?v=${encodeURIComponent(props.user.avatar_version)}`;
});

const bannerUser = computed<FederatedBannerUser>(() => ({
  displayName: currentDisplayName.value,
  username: props.user.username,
  avatarUrl: avatarUrl.value,
  avatarFallback: avatarLabel.value,
  isAdmin: props.user.is_admin,
}));

const bannerSites = computed(() =>
  createGhwizFederatedSites({
    authBaseUrl: centralAuthBaseUrl,
    goalsBaseUrl: import.meta.env.VITE_GOALS_BASE_URL,
    moneyPlannerBaseUrl: import.meta.env.VITE_MONEY_PLANNER_BASE_URL,
    agentBaseUrl: import.meta.env.VITE_AGENT_BASE_URL,
    apartmentGateBaseUrl: import.meta.env.VITE_APARTMENT_GATE_BASE_URL,
    fileShareBaseUrl: import.meta.env.VITE_FILE_SHARE_BASE_URL,
  }),
);

const localAccountItems = computed<FederatedBannerMenuItem[]>(() => {
  if (usesCentralAuth) {
    return [];
  }
  return [
    { id: "open-profile", label: "Edit Profile" },
    { id: "open-password", label: "Change Password" },
  ];
});

const appMenuItems = computed<FederatedBannerMenuItem[]>(() => {
  const items: FederatedBannerMenuItem[] = [
    {
      id: "open-notifications",
      label: props.notificationCount > 0
        ? `Notifications (${props.notificationCount})`
        : "Notifications",
    },
    { id: "open-shared-links", label: "Shared Links" },
  ];
  if (props.user.is_admin) {
    items.push({ id: "open-backups", label: "Backups" });
    items.push(
      usesCentralAuth
        ? { id: "central-invitation-codes", label: "Registration Codes", href: `${centralAuthBaseUrl}?tab=codes` }
        : { id: "open-invitation-codes", label: "Invitation Codes" },
    );
  }
  if (!usesCentralAuth) {
    items.push({ id: "delete-account", label: "Delete Account", danger: true });
  }
  return items;
});

const bannerAccountSettingsUrl = computed(() =>
  usesCentralAuth ? accountSettingsUrl(centralAuthBaseUrl) : "#",
);

function handleBannerAction(action: string): void {
  if (action === "open-profile") {
    emit("openProfile");
    return;
  }
  if (action === "open-password") {
    emit("openPassword");
    return;
  }
  if (action === "open-notifications") {
    emit("openNotifications");
    return;
  }
  if (action === "open-shared-links") {
    emit("openSharedLinks");
    return;
  }
  if (action === "open-backups") {
    emit("openBackups");
    return;
  }
  if (action === "open-invitation-codes") {
    emit("openInvitationCodes");
    return;
  }
  if (action === "delete-account") {
    emit("deleteAccount");
  }
}
</script>

<template>
  <FederatedBanner
    app-name="Goal Tracker"
    :app-url="appUrl"
    current-app-slug="goals"
    :account-settings-url="bannerAccountSettingsUrl"
    :account-items="localAccountItems"
    :app-items="appMenuItems"
    :sites="bannerSites"
    :user="bannerUser"
    @action="handleBannerAction"
    @sign-out="emit('logout')"
  />
</template>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-6);
  align-items: center;
  padding: var(--space-9) var(--space-10);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.brand-logo {
  width: auto;
  height: clamp(2.25rem, 5vw, 3.5rem);
  flex: 0 0 auto;
}

.brand-title {
  margin: 0;
  font-size: clamp(1.9rem, 4vw, 2.8rem);
}

.brand-title-mobile {
  display: none;
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
    margin-left: auto;
  }

  .brand-block {
    gap: var(--space-3);
  }

  .brand-logo {
    height: 2.25rem;
  }

  .brand-title {
    font-size: 1.35rem;
    line-height: 1;
  }

  .brand-title-desktop {
    display: none;
  }

  .brand-title-mobile {
    display: inline;
  }

  .version-badge {
    display: none;
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
