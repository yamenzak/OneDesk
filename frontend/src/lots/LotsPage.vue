<template>
  <!-- Lots (one_inventory/page/lots): batches and serial numbers as one tool.
       What each lot holds and where, which go off soon, each serial number
       and where it is, and the items kept in lots, with Track Lots and New
       Lot (one_inventory/lots.py, lots_actions.js). -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="!said.switched_on" class="mt-6 flex flex-wrap items-center gap-3 rounded-3 bg-surface-gray-2 px-4 py-3">
        <span class="lucide-info size-4 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-base text-ink-gray-7">{{ __("Items can't be kept in lots or by number yet.") }}</span>
        <Button v-if="said.can.switch" variant="solid" :label="__('Turn On')" @click="onedesk().lots.switch_on(load)" />
      </div>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <Switch v-if="shown === 'batches'" v-model="soon" :label="__('Going Off Only')" class="ms-1" />
        <Button v-if="item" variant="subtle" :label="__('Only {0}', [item])" :aria-label="__('Show Every Item')" @click="item = null">
          <template #suffix><span class="lucide-x size-3.5" aria-hidden="true" /></template>
        </Button>
      </div>

      <div class="mt-3">
        <LotRows v-if="shown === 'batches'" :lots="said.batches" :empty="search || soon ? __('No lots match') : __('No lots in stock')" />
        <SerialRows v-else-if="shown === 'serials'" :serials="said.serials" :empty="search ? __('No numbers match') : __('No serial numbers yet')" />
        <Rows v-else :rows="items" :empty="__('No item is kept in lots yet')" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, Switch, TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, ViewTabs, __, call, followList, onResize, onedesk, setQuery, viewWidth } from "../kit";
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
const soon = ref(!!props.query.soon);
// An item's page opens the page narrowed to that item.
const item = ref(props.query.item || null);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

let asked = 0;
async function load() {
  const mine = ++asked;
  const got = await call("onedesk.one_inventory.lots.read", { view: shown.value, search: search.value.trim() || null, soon: soon.value ? 1 : 0, item: item.value });
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
watch(soon, load);
watch(item, (now) => {
  setQuery("item", now);
  load();
});
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});

const views = computed(() => [
  { key: "batches", label: __("Lots"), count: said.value?.figures.lots || null },
  { key: "serials", label: __("Serial Numbers"), count: said.value?.figures.serials || null },
  { key: "items", label: __("Items") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.lots !== null && { title: __("Lots in Stock"), value: String(f.lots) },
    f.going_off !== null && { title: __("Going Off"), value: String(f.going_off), alarm: f.going_off > 0, note: f.going_off ? __("Within a month") : "" },
    f.gone !== null && { title: __("Gone Off"), value: String(f.gone), alarm: f.gone > 0 },
    f.serials !== null && { title: __("Numbered Pieces"), value: String(f.serials) },
  ].filter(Boolean);
});

// The items kept in lots or by number, and how: their numbering and how long a lot keeps.
const items = computed(() =>
  said.value.items.map((one) => ({
    key: one.name,
    label: one.item_name,
    sub: one.name,
    avatar: one.item_name,
    image: one.image,
    square: true,
    badge: one.has_batch_no ? __("Lots") : __("By Number"),
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

// A numbering pattern as the first number it gives, as frappe reads it:
// SL-.#### is SL-0001, LOT-.YYYY.-.### is LOT-2026-001.
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
  props.onTitle?.({ title: __("Lots") });
  extended(s);
  props.onActions?.(
    [
      s.switched_on && s.can.Batch && { label: __("New Lot"), primary: true, onClick: () => onedesk().lots.new_lot(null, load) },
      s.switched_on && s.can.Item && { label: __("Track Lots"), onClick: () => onedesk().lots.track(null, load) },
    ].filter(Boolean)
  );
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
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
