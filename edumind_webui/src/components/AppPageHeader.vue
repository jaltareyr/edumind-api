<template>
  <v-app-bar flat color="white" class="app-page-header" height="76">
    <v-container class="py-0" fluid>
      <div class="app-page-header__bar">
        <div class="app-page-header__brand">
          <v-avatar color="primary" size="48" variant="flat">
            <span class="app-page-header__brand-initials text-subtitle-1 font-weight-semibold">{{ organizationInitials }}</span>
          </v-avatar>
          <div>
            <p class="text-overline text-uppercase text-medium-emphasis mb-1">{{ organization }}</p>
            <h1 class="text-h5 font-weight-semibold mb-0">{{ title }}</h1>
          </div>
        </div>
        <div class="app-page-header__actions" v-if="hasVisibleActions || isAuthenticated">
          <div class="app-page-header__actions-left">
            <p v-if="description" class="text-body-2 text-medium-emphasis mb-0">{{ description }}</p>
            <div class="app-page-header__action-buttons">
              <v-btn
                v-if="showBack"
                variant="text"
                color="primary"
                prepend-icon="mdi-arrow-left"
                @click="handleBack"
              >
                Go Back
              </v-btn>
              <v-btn
                v-for="action in actions"
                :key="action.id"
                :variant="action.variant || 'flat'"
                :color="action.color || 'primary'"
                class="px-6"
                :prepend-icon="action.icon"
                :to="action.to"
                :disabled="action.disabled"
                :loading="action.loading"
                @click="handleActionClick(action)"
              >
                {{ action.label }}
              </v-btn>
            </div>
          </div>
          <div v-if="isAuthenticated" class="app-page-header__user">
            <v-menu location="bottom" transition="fade-transition">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  variant="text"
                  class="app-page-header__user-btn"
                >
                  <v-avatar size="36" color="primary" variant="flat">
                    <span class="app-page-header__user-initials">{{ userInitials }}</span>
                  </v-avatar>
                  <span class="app-page-header__user-name">{{ displayName }}</span>
                </v-btn>
              </template>
              <v-list density="comfortable" class="app-page-header__user-menu">
                <v-list-item>
                  <v-list-item-title>{{ displayName }}</v-list-item-title>
                  <v-list-item-subtitle class="text-capitalize">{{ role }}</v-list-item-subtitle>
                </v-list-item>
                <v-divider class="my-2" />
                <v-list-item @click="handleSignOut">
                  <v-list-item-title class="text-error">Sign out</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>
      </div>
    </v-container>
  </v-app-bar>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import { useAppStore, useUserStore } from '@/stores';

interface HeaderAction {
  id: string;
  label: string;
  icon?: string;
  variant?: 'flat' | 'text' | 'outlined';
  color?: string;
  to?: RouteLocationRaw;
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void | Promise<void>;
}

const props = withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    showBack?: boolean;
    actions?: HeaderAction[];
  }>(),
  {
    title: '',
    description: '',
    showBack: false,
    actions: () => [],
  }
);

const router = useRouter();
const appStore = useAppStore();
const userStore = useUserStore();

const organization = computed(() => appStore.organization);
const organizationInitials = computed(() => appStore.organizationInitials);
const actions = computed(() => props.actions ?? []);

const hasVisibleActions = computed(
  () => Boolean(props.description) || props.showBack || actions.value.length > 0
);

const isAuthenticated = computed(() => userStore.isAuthenticated);
const displayName = computed(() => userStore.displayName || 'EduMind Member');
const role = computed(() => userStore.role);
const userInitials = computed(() => {
  const name = displayName.value || '';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('') || 'EM';
});

const handleBack = () => {
  router.back();
};

const handleActionClick = (action: HeaderAction) => {
  if (typeof action.onClick === 'function') {
    action.onClick();
  }
};

const handleSignOut = async () => {
  await userStore.signOut();
  router.replace({ name: 'Login' });
};
</script>

<style scoped>
.app-page-header {
  border-bottom: 1px solid rgba(22, 101, 52, 0.12);
}

.app-page-header__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding-inline: 16px;
}

.app-page-header__brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-page-header__brand-initials {
  color: #ffffff;
}

.app-page-header__actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-page-header__actions-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.app-page-header__action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.app-page-header__user {
  display: flex;
  align-items: center;
}

.app-page-header__user-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-inline: 12px;
  text-transform: none;
}

.app-page-header__user-initials {
  color: #ffffff;
  font-weight: 600;
}

.app-page-header__user-name {
  font-weight: 600;
  color: rgba(15, 23, 42, 0.9);
}

.app-page-header__user-menu {
  min-width: 220px;
}

@media (max-width: 960px) {
  .app-page-header__bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .app-page-header__actions {
    width: 100%;
    justify-content: space-between;
  }

  .app-page-header__action-buttons {
    justify-content: flex-start;
  }
}
</style>
