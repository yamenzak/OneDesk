<template>
  <!-- The portal's frame: frappe-ui's DesktopShell with its Sidebar, or on a
       phone its MobileShell with a tab bar (Modelled on frappe-ui's own
       shells, as Helpdesk and Gameplan use them). -->
  <FrappeUIProvider>
    <MobileShell v-if="phone">
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
import { Avatar, DesktopShell, FrappeUIProvider, MobileNav, MobileNavItem, MobileShell } from "frappe-ui";

import PortalSidebar from "./parts/PortalSidebar.vue";
import { phone } from "./phone";
import { boot } from "./words";

const { tabs = [], me = {} } = boot();
</script>
