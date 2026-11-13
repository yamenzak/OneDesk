<template>
  <Page wide data-tour="one-marketplace">
    <Loading v-if="!said" />
    <MarketApp v-else-if="opened" :app="opened" :busy="busy" @back="open(null)" @turn="turn" />
    <template v-else>
      <div class="mt-6 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full sm:max-w-xs" type="search" :placeholder="__('Search Apps')" :aria-label="__('Search Apps')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <Dropdown v-if="said.fields.length" :options="fieldMenu">
          <template #trigger>
            <Button icon-left="lucide-briefcase" icon-right="lucide-chevron-down" :label="field ? fieldLabel(field) : __('Every Field')" />
          </template>
        </Dropdown>
        <TabButtons v-model="state" :options="states" class="ms-auto" />
      </div>

      <p v-if="!shown.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No apps match") }}</p>
      <div v-else class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <button
          v-for="one in shown"
          :key="one.id"
          type="button"
          class="flex items-start gap-3 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4 text-start hover:bg-surface-gray-2"
          @click="open(one.id)"
        >
          <span class="flex size-11 shrink-0 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-7"><Mark :name="one.mark" class="icon size-7" /></span>
          <span class="flex min-w-0 flex-1 flex-col gap-1">
            <span class="flex items-center justify-between gap-2">
              <span class="truncate text-base font-medium text-ink-gray-8">{{ one.name }}</span>
              <Badge v-if="one.on" :label="__('On')" theme="green" size="sm" />
              <Badge v-else-if="!one.plan.included" :label="planNeeded(one)" theme="gray" size="sm" />
            </span>
            <span class="line-clamp-2 text-sm text-ink-gray-5">{{ one.line }}</span>
          </span>
        </button>
      </div>

      <section class="mt-10">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ said.private.company ? __("Made for {0}", [said.private.company]) : __("Private Apps") }}</h2>
        <div v-if="said.private.apps.length" class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <div v-for="one in said.private.apps" :key="one.id" class="flex items-start gap-3 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4">
            <span class="flex size-11 shrink-0 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-7"><Mark :name="one.mark" class="icon size-7" /></span>
            <span class="flex min-w-0 flex-1 flex-col gap-1">
              <span class="flex items-center justify-between gap-2">
                <span class="truncate text-base font-medium text-ink-gray-8">{{ one.name }}</span>
                <Badge :label="PRIVATE[one.state]?.label || __('On')" :theme="PRIVATE[one.state]?.theme || 'green'" size="sm" />
              </span>
              <span class="text-sm text-ink-gray-5">{{ one.pitch || one.line }}</span>
              <span v-if="one.needs.length" class="text-sm text-ink-gray-5">{{ __("Needs {0}", [andList(one.needs)]) }}</span>
            </span>
          </div>
        </div>
        <div class="mt-4 flex max-w-xl flex-col gap-2">
          <span class="text-sm text-ink-gray-5">{{ __("Have a code for a private app? Type it here. Once installed, a private app stays on.") }}</span>
          <div class="flex items-center gap-2">
            <TextInput v-model="code" class="flex-1" type="text" autocomplete="off" spellcheck="false" placeholder="XXXX-XXXX-XXXX" :aria-label="__('Code')" @keydown.enter="claim" />
            <Button :label="__('Add')" :loading="claiming" @click="claim" />
          </div>
        </div>
      </section>
    </template>
  </Page>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Badge, Button, Dropdown, TabButtons, TextInput } from "frappe-ui";

import { Loading, Mark, Page, __, andList, call, escape, get, leaveTo, msgprint, name, onedesk, reloadPage, setQuery } from "../kit";
import MarketApp from "./MarketApp.vue";

const props = defineProps({ query: Object, onTitle: Function });

const said = ref(null);
const search = ref("");
const state = ref("all");
const field = ref("");
const at = ref(props.query?.app || "");
const busy = ref(false);
const code = ref("");
const claiming = ref(false);

const PRIVATE = {
  Installing: { label: __("Installing…"), theme: "blue" },
  Failed: { label: __("Couldn't be installed"), theme: "red" },
};

const states = [
  { label: __("All"), value: "all" },
  { label: __("On"), value: "on" },
  { label: __("Off"), value: "off" },
];

const load = async () => {
  said.value = await get("onedesk.one.marketplace.read");
};
load();

const opened = computed(() => said.value?.apps.find((one) => one.id === at.value) || null);

watch(
  () => props.query?.app,
  (app) => (at.value = app || ""),
);

watch(
  opened,
  (one) => props.onTitle?.(one ? { title: one.name } : { title: name("one_marketplace") }),
  { immediate: true },
);

const fieldLabel = (id) => said.value.fields.find((one) => one.id === id)?.label || id;
const fieldMenu = computed(() => [
  { label: __("Every Field"), onClick: () => (field.value = "") },
  ...said.value.fields.map((one) => ({ label: one.label, onClick: () => (field.value = one.id) })),
]);

const planNeeded = (one) => (one.plan.needs ? __("Needs the {0} plan", [one.plan.needs]) : __("Not in your plan"));

const shown = computed(() => {
  const words = onedesk().centers.search_words(search.value);
  return said.value.apps.filter(
    (one) =>
      (state.value === "all" || (state.value === "on") === one.on) &&
      (!field.value || one.fields.includes(field.value)) &&
      onedesk().centers.matches({ title: one.name, text: [one.line, one.pitch, ...one.brings].join(" ") }, words),
  );
});

function open(id) {
  at.value = id || "";
  setQuery("app", id || "", { push: Boolean(id) });
}

async function turn(one, on) {
  busy.value = true;
  try {
    const answer = await call("onedesk.one.marketplace.turn", { app: one.id, on: on ? 1 : 0 });
    const next = () => (answer.landing ? leaveTo(answer.landing) : reloadPage());
    if (!answer.said.length) return next();
    msgprint(answer.said.map(escape).join("<br>"), on ? __("{0} Turned On", [one.name]) : __("{0} Turned Off", [one.name])).onhide = next;
  } finally {
    busy.value = false;
  }
}

async function claim() {
  if (!code.value.trim()) return;
  claiming.value = true;
  try {
    const app = await call("onedesk.account_center.private.claim", { code: code.value.trim() });
    code.value = "";
    msgprint(
      app.state === "Installed"
        ? __("{0} is already installed.", [escape(app.title)])
        : __("{0} is being installed. It takes a few minutes, and appears here and on the rail when it's ready.", [escape(app.title)]),
      app.title,
    );
    await load();
  } finally {
    claiming.value = false;
  }
}
</script>
