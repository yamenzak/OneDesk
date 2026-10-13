<template>
  <!-- Stock on Hand (one_inventory/page/stock_on_hand): what the company holds
       now, in every warehouse or one, item by item (one_inventory/stock.py,
       read as the reader). -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="places" class="mt-5" />

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search Items')" :aria-label="__('Search Items')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <Switch v-model="lowOnly" :label="__('Low or Short Only')" class="ms-1" />
        <span class="ms-auto text-sm tabular-nums text-ink-gray-5">{{ counted }}</span>
      </div>

      <p v-if="!rows.length" class="py-10 text-center text-base text-ink-gray-5">{{ search || lowOnly ? __("No items match") : __("Nothing on hand here") }}</p>
      <List v-else :columns="columns" divider="full" :row-height="52" class="-mx-3 mt-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("On Hand") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Free to Sell") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("On Order") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Worth") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" row-key="item" v-slot="{ item }">
          <ListRow @click="go(`/desk/item/${encodeURIComponent(item.item)}`)">
            <ListCell class="min-w-0 gap-2">
              <div class="flex min-w-0 flex-col gap-0.5">
                <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                  <span class="truncate text-base text-ink-gray-8">{{ item.item_name }}</span>
                  <Badge v-if="item.low_in.length" :label="low(item)" theme="orange" size="sm" class="max-sm:hidden" />
                  <Badge v-if="item.free < 0" :label="__('{0} short', [quantity(-item.free, item.uom)])" theme="red" size="sm" class="max-sm:hidden" />
                </div>
                <span class="truncate text-sm text-ink-gray-5" :class="warned(item) && 'max-sm:hidden'">{{ [item.item !== item.item_name && item.item, item.group].filter(Boolean).join(" · ") }}</span>
                <span v-if="warned(item)" class="truncate text-sm sm:hidden" :class="item.free < 0 ? 'text-ink-red-5' : 'text-ink-amber-6'">{{ warned(item) }}</span>
              </div>
            </ListCell>
            <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ quantity(item.on_hand, item.uom) }}</ListCell>
            <ListCell class="justify-end whitespace-nowrap text-base tabular-nums max-md:hidden" :class="item.free < 0 ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ quantity(item.free, item.uom) }}</ListCell>
            <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-7 max-md:hidden">{{ item.on_order ? quantity(item.on_order, item.uom) : "" }}</ListCell>
            <ListCell class="justify-end text-base tabular-nums text-ink-gray-7 max-sm:hidden">{{ money(item.worth, said.currency) }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
      <p v-if="said.count > said.items.length" class="mt-3 text-sm text-ink-gray-5">{{ __("Showing {0} of {1}. Search to find the rest.", [count(said.items.length), count(said.count)]) }}</p>
    </template>
  </Page>
</template>

<script setup>
// What the stores hold now. ERPNext's Stock Balance answers it over a period
// and is prepared in the background, so the rail's first look at the stores
// was an empty page with a Generate button. This reads what ERPNext keeps
// current with every move, and each item opens its own page.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Badge, Switch, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Page, PlaceSpot, ViewTabs, __, call, count, followList, go, money, onResize, onedesk, quantity, setQuery, viewWidth } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.warehouse || "all");
const search = ref("");
const lowOnly = ref(false);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));
const columns = { base: ["minmax(0,1fr)", "auto"], sm: ["minmax(0,1fr)", "10rem", "9rem"], md: ["minmax(0,1fr)", "10rem", "10rem", "10rem", "9rem"] };

async function load() {
  const asked = shown.value;
  const got = await call("onedesk.one_inventory.stock.on_hand", { warehouse: asked === "all" ? null : asked });
  if (asked !== shown.value) return;
  said.value = got;
  report();
}

// Every move is a stock ledger entry; the page reads again when one is made.
let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = [followList("Stock Ledger Entry", soon), followList("Bin", soon)];
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("warehouse", now === "all" ? null : now);
  load();
}, { immediate: true });
watch(() => props.query.warehouse, (now) => (shown.value = now || "all"));

// A warehouse by its own name, without the company's letters after it.
const short = (name) => said.value?.warehouses.find((one) => one.name === name)?.label || name;
// On a phone the warnings take the second line, so a row stays one height.
const low = (item) => __("Low in {0}", [item.low_in.map(short).join(", ")]);
const warned = (item) => [item.low_in.length && low(item), item.free < 0 && __("{0} short", [quantity(-item.free, item.uom)])].filter(Boolean).join(" · ");
const places = computed(() => [
  { key: "all", label: __("All Warehouses") },
  ...(said.value?.warehouses || []).map((one) => ({ key: one.name, label: one.label, count: one.items || null })),
]);

const rows = computed(() => {
  const words = search.value.trim().toLowerCase();
  return (said.value?.items || []).filter(
    (one) =>
      (!words || one.item.toLowerCase().includes(words) || one.item_name.toLowerCase().includes(words)) &&
      (!lowOnly.value || one.low_in.length || one.free < 0)
  );
});
const counted = computed(() => (rows.value.length === 1 ? __("1 item") : __("{0} items", [count(rows.value.length)])));

const figures = computed(() => {
  const s = said.value;
  return [
    { title: __("Worth"), value: money(s.worth, s.currency), note: s.warehouse ? short(s.warehouse) : __("In every warehouse") },
    { title: __("Items"), value: count(s.count) },
    { title: __("Low"), value: count(s.low), alarm: s.low > 0, note: s.low ? __("At or below their reorder level") : "", action: s.low ? { icon: "lucide-filter", label: __("Show Low Items"), onClick: () => (lowOnly.value = true) } : null },
    { title: __("Short"), value: count(s.short), alarm: s.short > 0, note: s.short ? __("More promised than on hand") : "" },
  ];
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Stock on Hand") });
  extended(s);
  const warehouse = s.warehouse || undefined;
  props.onActions?.(
    [
      s.can["Stock Entry"] && { label: __("Move Stock"), primary: true, onClick: () => onedesk().stock.move(warehouse) },
      s.can["Stock Reconciliation"] && { label: __("Count Stock"), onClick: () => onedesk().stock.count(warehouse) },
      s.can.Warehouse && { label: __("Add Warehouse"), onClick: () => onedesk().stock.warehouse() },
      { label: __("Stock Balance"), onClick: () => go(`/desk/query-report/Stock Balance${warehouse ? `?warehouse=${encodeURIComponent(warehouse)}` : ""}`) },
      { label: __("Projected Stock"), onClick: () => go(`/desk/query-report/Stock Projected Qty${warehouse ? `?warehouse=${encodeURIComponent(warehouse)}` : ""}`) },
    ].filter(Boolean)
  );
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places_ = onedesk().places;
  if (!places_?.listening("oneinventory_stock.on_hand")) return;
  const data = {
    stock: {
      warehouse: s.warehouse,
      worth: s.worth,
      items: s.count,
      low: s.items.filter((one) => one.low_in.length).map((one) => one.item),
      short: s.items.filter((one) => one.free < 0).map((one) => one.item),
    },
  };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places_.emit("oneinventory_stock.on_hand", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
