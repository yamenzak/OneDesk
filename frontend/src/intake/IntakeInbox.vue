<template>
  <InterfacePart :win="win" part="commands" inline>
    <span class="inline-flex items-center gap-2">
      <TabButtons v-model="box" :options="boxes" />
      <Button variant="ghost" :label="__('Mark All as Read')" @click="seenAll" />
      <Switch v-if="mayEveryone" v-model="everyone" :label="everyonesLabel" />
    </span>
  </InterfacePart>

  <div class="flex h-full min-h-0 text-ink-gray-8" :class="{ 'max-md:flex-col': !win }">
    <div class="min-w-0 flex-1 overflow-auto" role="listbox" :aria-label="__('Documents')">
      <Loading v-if="loading && !items.length" />
      <div v-else-if="!items.length" class="flex flex-col items-center gap-2 py-16 text-ink-gray-5">
        <span :class="box === 'waiting' ? 'lucide-check-check' : 'lucide-inbox'" class="size-6" aria-hidden="true" />
        <span class="text-base">{{ box === "waiting" ? __("Nothing waiting") : __("No documents") }}</span>
      </div>
      <template v-else>
        <button
          v-for="one in items"
          :key="one.name"
          type="button"
          role="option"
          :aria-selected="one.name === reading"
          class="flex w-full flex-col gap-1 border-b border-outline-gray-1 px-4 py-3 text-start hover:bg-surface-gray-1"
          :class="{ 'bg-surface-gray-2 hover:bg-surface-gray-2': one.name === reading }"
          @click="read(one.name)"
        >
          <span class="flex items-center gap-2">
            <span v-if="one.unread" class="size-2 shrink-0 rounded-full bg-surface-blue-6" :aria-label="__('Unread')" />
            <span class="min-w-0 flex-1 truncate text-base" :class="one.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'">{{ one.title }}</span>
            <span class="shrink-0 text-sm text-ink-gray-5">{{ one.when ? ago(one.when) : "" }}</span>
          </span>
          <span class="flex flex-wrap items-center gap-1.5 text-sm text-ink-gray-5">
            <Badge v-if="one.kind" :label="one.kind" theme="blue" size="sm" />
            <Badge v-if="one.waiting" :label="__('{0} to decide', [one.waiting])" theme="amber" size="sm" />
            <span v-if="one.done">{{ __("{0} done", [one.done]) }}</span>
            <span v-if="one.person">· {{ one.person }}</span>
          </span>
          <span v-if="one.summary" class="line-clamp-2 text-sm text-ink-gray-6">{{ one.summary }}</span>
        </button>
        <div v-if="more" class="p-3">
          <Button variant="ghost" :label="__('More')" @click="load(items.length)" />
        </div>
      </template>
    </div>

    <component :is="win ? InterfacePart : 'section'" v-bind="win ? { win, part: 'details', detailsKey: 'intake', width: 440 } : { class: 'border-s border-outline-gray-1 md:w-[28rem]' }">
      <IntakeReading :reading="reading" @changed="changed" />
    </component>
  </div>
</template>

<script setup>
// Documents (one_ai/reading/inbox.py): every document that came in by
// mail, scan or upload, one line each, in two boxes as a mailbox has them,
// Waiting for what OneAI left a person to decide and Done for what it filed
// by itself. The one open is read in the window's details pane.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Badge, Button, Switch, TabButtons } from "frappe-ui";

import { Loading, InterfacePart, __, ago, call, hasRole, listen, setQuery } from "../kit";
import IntakeReading from "./IntakeReading.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  win: { type: Object, default: null },
  onTitle: Function,
});

const box = ref(props.query.box === "done" ? "done" : "waiting");
const everyone = ref(!!props.query.everyone);
const reading = ref(props.query.reading || null);
const items = ref([]);
const more = ref(false);
const loading = ref(false);
const waiting = ref(0);
const mayEveryone = hasRole("Workspace Administrator");
const everyonesLabel = __("Everyone's");

const boxes = computed(() => [
  { label: waiting.value ? __("Waiting ({0})", [waiting.value]) : __("Waiting"), value: "waiting" },
  { label: __("Done"), value: "done" },
]);

let asked = 0;
async function load(start = 0) {
  const mine = ++asked;
  loading.value = true;
  const said = await call("onedesk.one_ai.reading.inbox.listing", { box: box.value, everyone: everyone.value ? 1 : 0, start });
  if (mine !== asked) return;
  items.value = start ? [...items.value, ...said.items] : said.items;
  more.value = !!said.more;
  loading.value = false;
  counts();
}

async function counts() {
  const said = await call("onedesk.one_ai.reading.inbox.counts");
  waiting.value = said.waiting || 0;
}

function read(name) {
  reading.value = name;
  const one = items.value.find((row) => row.name === name);
  if (one) one.unread = false;
}

function changed() {
  load();
}

async function seenAll() {
  await call("onedesk.one_ai.reading.inbox.seen_all", { box: box.value });
  load();
}

watch(box, () => {
  reading.value = null;
  load();
});
watch(everyone, () => load());
watch([box, reading, everyone], () => {
  setQuery("box", box.value);
  setQuery("reading", reading.value || null);
  setQuery("everyone", everyone.value ? 1 : null);
});

props.onTitle?.(__("Documents"));
load();
onBeforeUnmount(listen("intake_inbox", () => load()));
</script>
