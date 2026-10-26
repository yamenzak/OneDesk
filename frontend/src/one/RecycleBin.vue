<template>
  <Page data-tour="one-bin">
    <Loading v-if="!said" />
    <template v-else>
      <ViewTabs v-model="state" :views="views" class="mt-4" data-tour="one-bin-states" />
      <div class="mt-4 flex flex-wrap items-center gap-2" data-tour="one-bin-filters">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <Select v-model="kind" class="w-48" :options="kindOptions" :aria-label="__('Kind')" />
        <TabButtons v-if="said.everyone" v-model="whose" :options="whoseButtons" class="ms-auto" />
      </div>

      <p v-if="!said.rows.length" class="py-16 text-center text-base text-ink-gray-5">{{ empty }}</p>
      <List v-else v-model:selection="selection" :selectable="state === 'deleted'" :columns="columns" class="mt-3 list-row-px-3" data-tour="one-bin-list">
        <ListGroup v-for="day in days" :key="day.key" :label="day.label">
          <ListRows :items="day.rows" row-key="name" v-slot="{ item, value }">
            <ListRow :value="value" class="hover:bg-surface-gray-2">
              <button type="button" class="absolute inset-0 rounded-3" :aria-label="item.title" @click="opened(item)" />
              <ListCell class="min-w-0">
                <div class="min-w-0">
                  <div class="truncate text-base text-ink-gray-8"><Branded :text="item.title" /></div>
                  <div class="truncate text-sm text-ink-gray-5">{{ item.kind }}<template v-if="said.everyone && whose === 'everyone'"> · {{ item.mine ? __("You") : item.by }}</template></div>
                </div>
              </ListCell>
              <ListCell class="justify-end whitespace-nowrap text-sm tabular-nums text-ink-gray-5 max-sm:hidden">{{ state === "restored" ? __("Put back {0}", [ago(item.back_on)]) : clock(item.on) }}</ListCell>
              <ListCell class="justify-end">
                <Button v-if="state === 'deleted'" class="relative" :label="__('Put Back')" @click="putBack([item.name])" />
                <Button v-else-if="item.new_name" class="relative" variant="ghost" :label="__('Open')" @click="go(record(item))" />
              </ListCell>
            </ListRow>
          </ListRows>
        </ListGroup>
      </List>
      <div v-if="said.more" class="mt-4 flex justify-center">
        <Button :label="__('Show More')" :loading="loading" @click="more" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Button, Select, TabButtons, TextInput } from "frappe-ui";
import { List, ListCell, ListGroup, ListRow, ListRows } from "frappe-ui/list";

import { Branded, Loading, Page, ViewTabs, __, ago, call, clock, date, followList, get, go, setQuery, toast, today, yesterday } from "../kit";

const props = defineProps({ query: { type: Object, default: () => ({}) }, onTitle: Function, onActions: Function, onStatus: Function });

const said = ref(null);
const state = ref(props.query.view === "restored" ? "restored" : "deleted");
const whose = ref(props.query.whose === "everyone" ? "everyone" : "mine");
const kind = ref(props.query.kind || "");
const search = ref("");
const selection = ref(new Set());
const loading = ref(false);

const asked = (start = 0) => get("onedesk.one.recycle.read", { whose: whose.value, state: state.value, kind: kind.value || null, search: search.value.trim() || null, start });

async function load() {
  said.value = await asked();
  selection.value = new Set();
  report();
}

async function more() {
  loading.value = true;
  const got = await asked(said.value.rows.length);
  said.value = { ...got, rows: [...said.value.rows, ...got.rows] };
  loading.value = false;
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 300);
};
load();
watch([state, whose, kind], () => {
  setQuery("view", state.value === "deleted" ? null : state.value);
  setQuery("whose", whose.value === "mine" ? null : whose.value);
  setQuery("kind", kind.value || null);
  load();
});
watch(search, soon);
watch(selection, report, { deep: true });
const stop = followList("Deleted Document", soon);
onBeforeUnmount(() => {
  stop();
  clearTimeout(timer);
});

const views = computed(() => [
  { key: "deleted", label: __("Deleted", null, "Recycle Bin"), count: said.value.counts.deleted || null },
  { key: "restored", label: __("Put Back"), count: said.value.counts.restored || null },
]);
const whoseButtons = computed(() => [
  { label: __("Yours"), value: "mine" },
  { label: __("Everyone's"), value: "everyone" },
]);
const kindOptions = computed(() => [{ label: __("Every Kind"), value: "" }, ...said.value.kinds.map((one) => ({ label: `${one.label} (${one.count})`, value: one.doctype }))]);
const columns = { default: ["minmax(0,1fr)", "auto"], sm: ["minmax(0,1fr)", "8rem", "auto"] };
const empty = computed(() => (search.value || kind.value ? __("Nothing matches") : state.value === "deleted" ? __("Nothing has been deleted.") : __("Nothing has been put back.")));

const dayOf = (value) => String(value || "").slice(0, 10);
const days = computed(() => {
  const now = today();
  const groups = [];
  for (const row of said.value.rows) {
    const key = dayOf(state.value === "restored" ? row.back_on : row.on);
    let group = groups.at(-1);
    if (!group || group.key !== key) {
      group = { key, label: key === now ? __("Today") : key === yesterday() ? __("Yesterday") : date(key), rows: [] };
      groups.push(group);
    }
    group.rows.push(row);
  }
  return groups;
});

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const record = (item) => `/desk/${slug(item.doctype)}/${encodeURIComponent(item.new_name)}`;
const opened = (item) => go(`/desk/deleted-document/${encodeURIComponent(item.name)}`);

async function putBack(names) {
  const got = await call("onedesk.one.recycle.bulk_restore", { names });
  const parts = [];
  if (got.restored.length) parts.push(got.restored.length === 1 ? __("1 put back.") : __("{0} put back.", [got.restored.length]));
  if (got.already.length) parts.push(__("{0} were back already.", [got.already.length]));
  if (got.failed.length) parts.push(got.failed.length === 1 ? __("1 could not be put back. Open it to see why.") : __("{0} could not be put back. Open each to see why.", [got.failed.length]));
  toast(parts.join(" "));
  load();
}

function report() {
  props.onTitle?.({ title: __("Recycle Bin") });
  const chosen = [...selection.value];
  props.onActions?.(chosen.length ? [{ label: chosen.length === 1 ? __("Put Back 1") : __("Put Back {0}", [chosen.length]), primary: true, onClick: () => putBack(chosen) }] : []);
}
</script>
