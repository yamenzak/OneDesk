<template>
  <Sidebar :aria-label="__('Portal')" :collapsible="false">
    <SidebarHeader :title="me.party || me.name" :subtitle="me.party ? me.name : ''" logo="/assets/onedesk/images/one.svg" :menu-items="menu" />
    <div class="flex-1 overflow-y-auto px-2 pb-3">
      <SidebarItem :label="__('Home')" icon="lucide-house" :route="{ name: 'Home' }" :active="here === ''" />
      <SidebarItem
        v-for="tab in tabs"
        :key="tab.path"
        :label="tab.title"
        :icon="`lucide-${tab.icon}`"
        :route="`/${tab.path}`"
        :active="here === tab.path"
      />
      <SidebarLabel class="mt-4">{{ __("Account") }}</SidebarLabel>
      <SidebarItem
        v-for="page in account"
        :key="page.path"
        :label="page.title"
        :icon="`lucide-${page.icon}`"
        :route="`/${page.path}`"
        :active="here === page.path"
      />
    </div>
  </Sidebar>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Sidebar, SidebarHeader, SidebarItem, SidebarLabel } from "frappe-ui";

import { __, boot } from "../words";

const { tabs = [], account = [], me = {} } = boot();
const route = useRoute();
const here = computed(() => route.path.split("/")[1]);
const go = (where) => () => (window.location.href = where);
const menu = [
  { label: __("Privacy Policy"), icon: "lucide-scale", onClick: go("/legal/privacy") },
  { label: __("Sign Out"), icon: "lucide-log-out", onClick: go("/logout") },
];
</script>
