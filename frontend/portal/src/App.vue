<template>
  <FrappeUIProvider>
    <MobileShell v-if="phone && bare"><RouterView /></MobileShell>
    <DesktopShell v-else-if="bare" class="bare"><RouterView /></DesktopShell>
    <MobileShell v-else-if="phone">
      <RouterView />
      <template #nav>
        <MobileNav>
          <MobileNavItem :label="__('Home')" icon="lucide-house" :route="{ name: 'Home' }" />
          <MobileNavItem
            v-for="tab in tabs.slice(0, 3)"
            :key="tab.path"
            :label="tab.title"
            :icon="`lucide-${tab.icon}`"
            :route="`/${tab.path}`"
          />
          <MobileNavItem :label="__('More')" :route="{ name: 'Menu' }">
            <Avatar :label="me.name" :image="me.image" size="md" />
          </MobileNavItem>
        </MobileNav>
      </template>
    </MobileShell>
    <DesktopShell v-else>
      <template #sidebar><PortalSidebar /></template>
      <RouterView />
    </DesktopShell>
  </FrappeUIProvider>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Avatar, DesktopShell, FrappeUIProvider, MobileNav, MobileNavItem, MobileShell } from "frappe-ui";

import PortalSidebar from "./parts/PortalSidebar.vue";
import { phone } from "./phone";
import { boot } from "./words";

const { tabs = [], me = {} } = boot();
const route = useRoute();
const bare = computed(() => boot().guest || route.meta.bare);
</script>
