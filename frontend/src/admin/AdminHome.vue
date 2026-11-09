<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Section :title="__('Needs You')" icon="lucide-triangle-alert" :aside="said.needs.length || ''">
        <p v-if="!said.needs.length" class="py-3 text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <div v-else class="rounded-4 border border-outline-gray-1 bg-surface-elevation-2">
          <div v-for="one in said.needs" :key="one.title" class="flex items-center gap-3 border-t border-outline-gray-1 px-4 py-2.5 first:border-t-0">
            <div class="min-w-0 flex-1">
              <div class="text-base font-medium text-ink-gray-9">{{ one.title }}</div>
              <div v-if="one.detail || one.why" class="text-sm text-ink-gray-5">{{ one.detail || one.why }}</div>
            </div>
            <Badge v-if="one.badge" :label="one.badge" theme="amber" />
            <Button v-if="one.action" :label="one.action.label" @click="act(one.action)" />
            <Button v-else :label="__('View')" @click="goTo('Form', one.doctype, one.name)" />
          </div>
        </div>
      </Section>
      <Section :title="__('The Business')" icon="lucide-chart-column">
        <Figures :figures="figures" />
      </Section>
      <Section :title="__('Servers')" icon="lucide-server" :action="{ text: true, label: __('All Servers'), onClick: () => go('oneadmin-servers') }">
        <ServerRows :rows="said.servers" />
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Badge, Button } from "frappe-ui";

import { Figures, Loading, Page, Section, __, call, count, followList, get, go, goTo, money } from "../kit";
import ServerRows from "./ServerRows.vue";

const said = ref(null);
const load = async () => (said.value = await get("onedesk.one_admin.console.overview"));
const figures = computed(() => [
  { title: __("Live Workspaces"), value: count(said.value.live), route: "List/Tenant" },
  { title: __("Monthly Revenue"), value: money(said.value.revenue, said.value.currency, 0) },
  { title: __("Server Cost"), value: `$${count(said.value.cost)}`, note: __("A month") },
  { title: __("Servers"), value: count(said.value.servers.length), route: "oneadmin-servers" },
]);
async function act(action) {
  await call(action.method, action.args);
  await load();
}
let timer;
let stops = [];
onMounted(() => {
  load();
  stops = ["Tenant", "Offering", "Workspace Server"].map((doctype) => followList(doctype, load));
  timer = setInterval(load, 60000);
});
onBeforeUnmount(() => {
  clearInterval(timer);
  stops.forEach((stop) => stop());
});
</script>
