<template>
  <Page data-tour="one-dashboards">
    <Loading v-if="!said" />
    <template v-else>
      <TextInput v-model="search" class="mt-5 w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')" data-tour="one-dashboards-search">
        <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
      </TextInput>
      <p v-if="!groups.length" class="py-16 text-center text-base text-ink-gray-5">{{ search ? __("Nothing matches") : __("There are no dashboards you can read.") }}</p>
      <Section v-for="group in groups" :key="group.app" :title="group.label" :aside="group.rows.length" data-tour="one-dashboards-group">
        <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <li v-for="one in group.rows" :key="one.name">
            <button type="button" class="flex w-full items-start gap-3 rounded-4 border border-outline-gray-1 px-4 py-3 text-start hover:bg-surface-gray-2 focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/dashboard-view/${encodeURIComponent(one.name)}`)">
              <span class="lucide-layout-dashboard mt-0.5 size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
              <span class="min-w-0">
                <span class="block truncate text-base text-ink-gray-8">{{ one.title }}</span>
                <span class="block text-sm text-ink-gray-5">{{ made(one) }}</span>
              </span>
            </button>
          </li>
        </ul>
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { TextInput } from "frappe-ui";

import { Loading, Page, Section, __, followList, get, go, newDoc } from "../kit";

const props = defineProps({ onTitle: Function, onActions: Function });

const said = ref(null);
const search = ref("");

function load() {
  get("onedesk.one.dashboards.read").then((got) => {
    said.value = got;
    props.onTitle?.({ title: __("Dashboards") });
    props.onActions?.(got.makes ? [{ label: __("New Dashboard"), primary: true, onClick: () => newDoc("Dashboard") }] : []);
  });
}
load();
const unheard = ["Dashboard", "Sidebar Item"].map((one) => followList(one, load));
onBeforeUnmount(() => unheard.forEach((one) => one()));

const groups = computed(() => {
  const words = search.value.trim().toLowerCase();
  const out = [];
  for (const one of said.value.rows) {
    if (words && !`${one.title} ${one.app}`.toLowerCase().includes(words)) continue;
    let group = out.find((two) => two.app === one.app);
    if (!group) out.push((group = { app: one.app, label: one.app === "Made Here" ? said.value.here : one.app, rows: [] }));
    group.rows.push(one);
  }
  return out;
});

function made(one) {
  const charts = one.charts === 1 ? __("1 chart") : __("{0} charts", [one.charts]);
  const cards = one.cards === 1 ? __("1 number") : __("{0} numbers", [one.cards]);
  const parts = [one.charts && charts, one.cards && cards].filter(Boolean).join(" · ");
  return one.by ? `${parts} · ${__("Made by {0}", [one.by])}` : parts;
}
</script>
