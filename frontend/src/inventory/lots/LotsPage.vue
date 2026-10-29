<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="!said.switched_on" class="mt-6 flex flex-wrap items-center gap-3 rounded-3 bg-surface-gray-2 px-4 py-3">
        <span class="lucide-info size-4 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-base text-ink-gray-7">{{ __("Items can't be kept in batches or by Serial No yet.") }}</span>
        <Button v-if="said.can.switch" variant="solid" :label="__('Turn On')" @click="onedesk().lots.switch_on(load)" />
      </div>
      <Figures :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <TabButtons v-if="shown === 'batches' && states.length > 1" v-model="state" :options="states" class="ms-auto" />
        <Button v-if="item" variant="subtle" :label="__('Only {0}', [item])" :aria-label="__('Show Every Item')" @click="item = null">
          <template #suffix><span class="lucide-x size-3.5" aria-hidden="true" /></template>
        </Button>
      </div>

      <div class="mt-3">
        <LotRows v-if="shown === 'batches'" :lots="lots" :empty="search || state !== 'all' ? __('No batches match') : __('No batches in stock')" />
        <SerialRows v-else-if="shown === 'serials'" :serials="said.serials" :empty="search ? __('No Serial Nos match') : __('No Serial Nos yet')" />
        <Rows v-else :rows="items" :empty="__('No item is kept in batches yet')" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, TabButtons, TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, ViewTabs, __, call, count, followList, onResize, onedesk, setQuery, viewWidth } from "../../kit";
import LotRows from "./LotRows.vue";
import SerialRows from "./SerialRows.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.view || "batches");
const search = ref("");
const state = ref(props.query.soon ? "soon" : "all");
const item = ref(props.query.item || null);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

let asked = 0;
async function load() {
  const mine = ++asked;
  const got = await call("onedesk.one_inventory.lots.read", { view: shown.value, search: search.value.trim() || null, item: item.value });
  if (mine !== asked) return;
  said.value = got;
  report();
}
load();

let timer = null;
const soonLoad = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Batch", "Serial No", "Item"].map((one) => followList(one, soonLoad));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("view", now === "batches" ? null : now);
  load();
});
watch(state, (now) => setQuery("soon", now === "soon" ? 1 : null));
watch(item, (now) => {
  setQuery("item", now);
  load();
});
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});

const lots = computed(() => {
  const all = said.value?.batches || [];
  if (state.value === "soon") return all.filter((one) => one.state);
  if (state.value === "gone") return all.filter((one) => one.state === "Expired");
  return all;
});
const states = computed(() => {
  const f = said.value?.figures || {};
  return [
    { value: "all", label: __("All") },
    (f.going_off || f.gone) && { value: "soon", label: __("Expiring Soon {0}", [count((f.going_off || 0) + (f.gone || 0))]) },
    f.gone && { value: "gone", label: __("Expired {0}", [count(f.gone)]) },
  ].filter(Boolean);
});

const views = computed(() => [
  { key: "batches", label: __("Batches"), count: said.value?.figures.lots || null },
  { key: "serials", label: __("Serial Nos"), count: said.value?.figures.serials || null },
  { key: "items", label: __("Items") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.lots !== null && { title: __("Batches in Stock"), value: count(f.lots) },
    f.going_off !== null && { title: __("Expiring Soon"), value: count(f.going_off), alarm: f.going_off > 0, note: f.going_off ? __("Within a month") : "", action: f.going_off ? { icon: "lucide-filter", label: __("Show Batches Expiring Soon"), onClick: () => (state.value = "soon") } : null },
    f.gone !== null && { title: __("Expired"), value: count(f.gone), alarm: f.gone > 0, action: f.gone ? { icon: "lucide-filter", label: __("Show Expired Batches"), onClick: () => (state.value = "gone") } : null },
    f.serials !== null && { title: __("Serial Nos"), value: count(f.serials) },
  ].filter(Boolean);
});

const items = computed(() =>
  said.value.items.map((one) => ({
    key: one.name,
    label: one.item_name,
    sub: one.name,
    avatar: one.item_name,
    image: one.image,
    square: true,
    badge: one.has_batch_no ? __("Batch") : __("Serial No"),
    below: [
      one.has_batch_no && (one.create_new_batch ? (one.batch_number_series ? __("Numbered like {0}", [example(one.batch_number_series)]) : __("Numbered automatically")) : __("Numbered by hand")),
      one.has_batch_no && one.has_expiry_date && one.shelf_life_in_days ? __("Keeps {0} days", [one.shelf_life_in_days]) : "",
      one.has_serial_no && one.serial_no_series ? __("Numbered like {0}", [example(one.serial_no_series)]) : "",
    ]
      .filter(Boolean)
      .join(" · "),
    route: `/desk/item/${encodeURIComponent(one.name)}?view=stock`,
  }))
);

function example(series) {
  const today = new Date();
  const parts = { YYYY: String(today.getFullYear()), YY: String(today.getFullYear()).slice(2), MM: String(today.getMonth() + 1).padStart(2, "0"), DD: String(today.getDate()).padStart(2, "0") };
  return series
    .split(".")
    .map((part) => (/^#+$/.test(part) ? "1".padStart(part.length, "0") : parts[part] ?? part))
    .join("");
}

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Batch and Serial No") });
  extended(s);
  props.onActions?.(
    [
      s.switched_on && s.can.Batch && { label: __("New Batch"), primary: true, onClick: () => onedesk().lots.new_lot(null, load) },
      s.switched_on && s.can.Item && { label: __("Track Batches"), onClick: () => onedesk().lots.track(null, load) },
    ].filter(Boolean)
  );
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_lots.shown")) return;
  const data = { lots: { view: shown.value, ...s.figures } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_lots.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
