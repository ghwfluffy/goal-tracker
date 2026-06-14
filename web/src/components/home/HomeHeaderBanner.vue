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

const bannerSites = computed(() => {
  if (!usesCentralAuth) {
    return [];
  }
  return createGhwizFederatedSites({
    authBaseUrl: centralAuthBaseUrl,
    goalsBaseUrl: import.meta.env.VITE_GOALS_BASE_URL,
    moneyPlannerBaseUrl: import.meta.env.VITE_MONEY_PLANNER_BASE_URL,
    agentBaseUrl: import.meta.env.VITE_AGENT_BASE_URL,
    apartmentGateBaseUrl: import.meta.env.VITE_APARTMENT_GATE_BASE_URL,
    fileShareBaseUrl: import.meta.env.VITE_FILE_SHARE_BASE_URL,
  });
});

const localAccountItems = computed<FederatedBannerMenuItem[]>(() => {
  if (usesCentralAuth) {
    return [];
  }
  return [
    { id: "open-profile", label: "Edit Profile" },
    { id: "open-password", label: "Change Password" },
  ];
});

const bannerActionItems = computed<FederatedBannerMenuItem[]>(() => [
  {
    id: "open-notifications",
    label: props.notificationCount > 0
      ? `Notifications (${props.notificationCount})`
      : "Notifications",
    icon: "bell",
    badge: props.notificationCount > 0 ? props.notificationCount : null,
  },
]);

const appMenuItems = computed<FederatedBannerMenuItem[]>(() => {
  const items: FederatedBannerMenuItem[] = [
    { id: "open-shared-links", label: "Shared Links" },
  ];
  if (props.user.is_admin) {
    items.push({ id: "open-backups", label: "Backups" });
    if (!usesCentralAuth) {
      items.push({ id: "open-invitation-codes", label: "Invitation Codes" });
    }
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
    :action-items="bannerActionItems"
    :app-items="appMenuItems"
    :sites="bannerSites"
    :user="bannerUser"
    @action="handleBannerAction"
    @sign-out="emit('logout')"
  />
</template>
