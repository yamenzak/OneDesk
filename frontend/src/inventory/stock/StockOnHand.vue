<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures data-tour="oneinventory-stock-figures" :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />

      <div ref="finder" data-tour="oneinventory-stock-find" class="mt-6 flex flex-wrap items-center gap-2">
        <Dropdown :options="placeMenu">
          <template #trigger>
            <Button icon-left="lucide-warehouse" icon-right="lucide-chevron-down" :label="shown === 'all' ? __('All Warehouses') : short(shown)" />
          </template>
        </Dropdown>
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search Items')" :aria-label="__('Search Items')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <TabButtons v-if="states.length > 1" v-model="state" :options="states" class="ms-auto" />
      </div>

      <p v-if="!rows.length" class="py-10 text-center text-base text-ink-gray-5">{{ search || state !== "all" ? __("No items match") : __("Nothing on hand here") }}</p>
      <List data-tour="oneinventory-stock-list" v-else :columns="columns" divider="full" :row-height="60" class="-mx-3 mt-3 list-gap-4 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell class="max-lg:hidden">{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-xl:hidden">{{ __("Actual Qty") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-xl:hidden">{{ __("Reserved Qty") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Available Qty") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-lg:hidden">{{ __("Ordered Qty") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Stock Value") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" row-key="item" v-slot="{ item }">
          <ListRow @click="go(`/desk/item/${encodeURIComponent(item.item)}`)">
            <ListCell class="min-w-0 gap-3">
              <Avatar :label="item.item_name" :image="item.image" shape="square" size="xl" />
              <div class="flex min-w-0 flex-col gap-1">
                <span class="truncate text-base font-medium text-ink-gray-8">{{ item.item_name }}</span>
                <div class="flex min-w-0 items-center gap-2">
                  <Badge :label="STATE[item.state].label" :theme="STATE[item.state].theme" size="sm" class="lg:hidden" />
                  <span class="truncate text-sm text-ink-gray-5">{{ [item.item !== item.item_name && item.item, item.group].filter(Boolean).join(" · ") }}</span>
                </div>
              </div>
            </ListCell>
            <ListCell class="max-lg:hidden"><Badge :label="STATE[item.state].label" :theme="STATE[item.state].theme" size="md" :title="note(item)" /></ListCell>
            <ListCell v-for="key in ['on_hand', 'committed', 'free', 'on_order']" :key="key" class="justify-end whitespace-nowrap tabular-nums" :class="SHOWN[key]">
              <span v-if="item[key]" class="text-base" :class="item[key] < 0 ? 'text-ink-red-5' : key === 'free' ? 'text-ink-gray-8' : 'text-ink-gray-7'">{{ quantity(item[key]) }}</span>
              <span v-else class="text-base text-ink-gray-4">–</span>
              <span v-if="item[key]" class="ms-1 text-sm text-ink-gray-5">{{ __(item.unit) }}</span>
            </ListCell>
            <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-7 max-sm:hidden">{{ money(item.worth, said.currency) }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
      <p v-if="said.count > said.items.length" class="mt-3 text-sm text-ink-gray-5">{{ __("Showing {0} of {1}. Search to find the rest.", [count(said.items.length), count(said.count)]) }}</p>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown, TabButtons, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Page, PlaceSpot, __, call, count, followList, go, money, onResize, onedesk, quantity, shortcut, setQuery, viewWidth } from "../../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.warehouse || "all");
const search = ref("");
const state = ref("all");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));
const columns = {
  base: ["minmax(0,1fr)", "auto"],
  sm: ["minmax(0,1fr)", "8rem", "9rem"],
  lg: ["minmax(0,1fr)", "6.5rem", "8rem", "8rem", "9rem"],
  xl: ["minmax(0,1fr)", "6.5rem", "8rem", "8rem", "8rem", "8rem", "9rem"],
};
const SHOWN = { on_hand: "max-xl:hidden", committed: "max-xl:hidden", free: "", on_order: "max-lg:hidden" };
const STATE = {
  in: { label: __("In Stock"), theme: "green" },
  low: { label: __("Low"), theme: "amber" },
  short: { label: __("Short"), theme: "red" },
  out: { label: __("Out of Stock"), theme: "gray" },
};

async function load() {
  const asked = shown.value;
  const got = await call("onedesk.one_inventory.stock.on_hand", { warehouse: asked === "all" ? null : asked });
  if (asked !== shown.value) return;
  said.value = got;
  report();
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Stock Ledger Entry", "Bin", "Item", "Warehouse", "UOM"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("warehouse", now === "all" ? null : now);
  load();
}, { immediate: true });
watch(() => props.query.warehouse, (now) => (shown.value = now || "all"));

const short = (name) => said.value?.warehouses.find((one) => one.name === name)?.label || name;
const note = (item) =>
  item.state === "low"
    ? __("Low in {0}", [item.low_in.map(short).join(", ")])
    : item.state === "short"
      ? __("{0} short", [quantity(-item.free, item.uom)])
      : "";
const placeMenu = computed(() => [
  { label: __("All Warehouses"), onClick: () => (shown.value = "all") },
  ...(said.value?.warehouses || []).map((one) => ({
    label: one.label,
    onClick: () => (shown.value = one.name),
  })),
]);
const states = computed(() => {
  const s = said.value;
  return [
    { value: "all", label: __("All") },
    s.low && { value: "low", label: __("Low {0}", [count(s.low)]) },
    s.short && { value: "short", label: __("Short {0}", [count(s.short)]) },
    s.out && { value: "out", label: __("Out of Stock {0}", [count(s.out)]) },
  ].filter(Boolean);
});

const rows = computed(() => {
  const words = search.value.trim().toLowerCase();
  return (said.value?.items || []).filter(
    (one) =>
      (!words || one.item.toLowerCase().includes(words) || one.item_name.toLowerCase().includes(words)) &&
      (state.value === "all" || one.state === state.value)
  );
});

const figures = computed(() => {
  const s = said.value;
  return [
    { title: __("Stock Value"), value: money(s.worth, s.currency), note: s.warehouse ? short(s.warehouse) : __("In every warehouse") },
    { title: __("Items"), value: count(s.count) },
    { title: __("Low"), value: count(s.low), alarm: s.low > 0, note: s.low ? __("At or below their reorder level") : "", action: s.low ? { icon: "lucide-filter", label: __("Show Low Items"), onClick: () => (state.value = "low") } : null },
    { title: __("Short"), value: count(s.short), alarm: s.short > 0, note: s.short ? __("More promised than on hand") : "", action: s.short ? { icon: "lucide-filter", label: __("Show Short Items"), onClick: () => (state.value = "short") } : null },
  ];
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Stock Summary") });
  extended(s);
  const warehouse = s.warehouse || undefined;
  props.onActions?.(
    [
      s.can["Stock Entry"] && { label: __("Transfer Stock"), primary: true, onClick: () => onedesk().stock.move(warehouse) },
      s.can["Stock Reconciliation"] && { label: __("Count Stock"), onClick: () => onedesk().stock.count(warehouse) },
      s.can.Warehouse && { label: __("Add Warehouse"), onClick: () => onedesk().stock.warehouse() },
      { label: __("Stock Balance"), onClick: () => go(`/desk/query-report/Stock Balance${warehouse ? `?warehouse=${encodeURIComponent(warehouse)}` : ""}`) },
      { label: __("Stock Projected Qty"), onClick: () => go(`/desk/query-report/Stock Projected Qty${warehouse ? `?warehouse=${encodeURIComponent(warehouse)}` : ""}`) },
    ].filter(Boolean)
  );
}

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

const finder = ref(null);
const find = () => finder.value?.querySelector("input[type=search]")?.focus();
const forget = [shortcut("one_inventory.find_stock", find)];
onBeforeUnmount(() => forget.forEach((one) => one()));
</script>
