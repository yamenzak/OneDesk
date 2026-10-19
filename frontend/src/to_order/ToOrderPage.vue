<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />

      <div class="mt-6 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <TabButtons v-if="reasons.length > 1" v-model="reason" :options="reasons" class="ms-auto" />
      </div>

      <p v-if="!lines.length" class="py-10 text-center text-base text-ink-gray-5">{{ search || reason !== "all" ? __("Nothing matches") : __("Nothing to order") }}</p>
      <List v-else v-model:selection="picked" :selectable="said.can.order" :columns="columns" divider="full" :row-height="60" class="-mx-3 mt-3 list-gap-4 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell class="max-sm:hidden">{{ __("Why") }}</ListHeaderCell>
          <ListHeaderCell class="max-lg:hidden">{{ __("Supplier") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Qty") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-xl:hidden">{{ __("Cost") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="lines" row-key="key" v-slot="{ item, value }">
          <ListRow :value="value">
            <ListCell class="min-w-0 gap-3">
              <Avatar :label="item.item_name" :image="item.image" shape="square" size="xl" />
              <div class="flex min-w-0 flex-col gap-1">
                <span class="truncate text-base font-medium text-ink-gray-8">{{ item.item_name }}</span>
                <div class="flex min-w-0 items-center gap-2">
                  <Badge :label="WHY[item.why].label" :theme="WHY[item.why].theme" size="sm" class="sm:hidden" />
                  <span class="truncate text-sm text-ink-gray-5">{{ [item.item_code !== item.item_name && item.item_code, item.warehouse_label].filter(Boolean).join(" · ") }}</span>
                </div>
              </div>
            </ListCell>
            <ListCell class="max-sm:hidden">
              <div class="flex min-w-0 flex-col items-start gap-1">
                <Badge :label="WHY[item.why].label" :theme="WHY[item.why].theme" size="md" />
                <span class="max-w-full truncate text-sm text-ink-gray-5">{{ because(item) }}</span>
              </div>
            </ListCell>
            <ListCell class="max-lg:hidden">
              <div class="flex min-w-0 flex-col items-start gap-1">
                <span v-if="item.supplier" class="max-w-full truncate text-base text-ink-gray-8">{{ item.supplier_name }}</span>
                <span v-else class="text-base text-ink-gray-4">{{ __("No supplier yet") }}</span>
                <span v-if="item.rate" class="max-w-full truncate text-sm text-ink-gray-5">{{ __("Last paid {0} a {1}", [money(item.rate, said.currency), __(item.unit)]) }}</span>
              </div>
            </ListCell>
            <ListCell class="justify-end whitespace-nowrap tabular-nums">
              <span class="text-base font-medium text-ink-gray-8">{{ quantity(item.qty) }}</span>
              <span class="ms-1 text-sm text-ink-gray-5">{{ __(item.unit) }}</span>
            </ListCell>
            <ListCell class="justify-end whitespace-nowrap text-base tabular-nums max-xl:hidden" :class="item.cost === null ? 'text-ink-gray-4' : 'text-ink-gray-7'">
              {{ item.cost === null ? "–" : money(item.cost, said.currency) }}
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge, TabButtons, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Page, PlaceSpot, __, alert, call, confirm, count, followList, fromToday, go, money, newDoc, onResize, onedesk, prompt, quantity, viewWidth } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const search = ref("");
const reason = ref(props.query.why || "all");
const picked = ref([]);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));
const columns = {
  base: ["minmax(0,1fr)", "auto"],
  sm: ["minmax(0,1fr)", "11rem", "8rem"],
  lg: ["minmax(0,1fr)", "11rem", "13rem", "8rem"],
  xl: ["minmax(0,1fr)", "17rem", "13rem", "7rem", "8rem"],
};
const WHY = {
  requested: { label: __("Requested"), theme: "blue" },
  low: { label: __("Running Low"), theme: "amber" },
};

async function load() {
  said.value = await call("onedesk.one_inventory.order.read");
  const there = new Set(said.value.lines.map((one) => one.key));
  picked.value = picked.value.filter((key) => there.has(key));
  report();
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Material Request", "Purchase Order", "Bin", "Item", "Supplier", "Warehouse", "UOM", "Project"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(picked, () => said.value && report());

const because = (one) =>
  one.why === "requested"
    ? [one.project_title || one.material_request, one.needed_by && __("needed {0}", [fromToday(one.needed_by)])].filter(Boolean).join(" · ")
    : __("{0} left, reorder at {1}", [quantity(one.projected), quantity(one.level)]);

const reasons = computed(() => {
  const f = said.value.figures;
  return [
    { value: "all", label: __("All") },
    f.requested && { value: "requested", label: __("Requested {0}", [count(f.requested)]) },
    f.low && { value: "low", label: __("Running Low {0}", [count(f.low)]) },
  ].filter(Boolean);
});

const lines = computed(() => {
  const words = search.value.trim().toLowerCase();
  return (said.value?.lines || []).filter(
    (one) =>
      (reason.value === "all" || one.why === reason.value) &&
      (!words || [one.item_code, one.item_name, one.supplier_name, one.material_request].some((text) => text?.toLowerCase().includes(words)))
  );
});

const figures = computed(() => {
  const f = said.value.figures;
  return [
    { title: __("Items"), value: count(f.lines), note: f.suppliers ? __("From {0} suppliers", [count(f.suppliers)]) : "" },
    { title: __("Requested"), value: count(f.requested), note: f.requested ? __("Asked for and not ordered yet") : "", action: f.requested ? { icon: "lucide-filter", label: __("Show Requested"), onClick: () => (reason.value = "requested") } : null },
    { title: __("Running Low"), value: count(f.low), alarm: f.low > 0, note: f.low ? __("At or below their reorder level") : "", action: f.low ? { icon: "lucide-filter", label: __("Show Running Low"), onClick: () => (reason.value = "low") } : null },
    { title: __("Cost"), value: money(f.cost, said.value.currency), note: f.unpriced ? __("{0} lines never bought before", [count(f.unpriced)]) : __("Before tax, at the last prices paid") },
  ];
});

function order() {
  const chosen = picked.value.length ? said.value.lines.filter((one) => picked.value.includes(one.key)) : lines.value;
  if (!chosen.length) return;
  const send = (supplier) =>
    call("onedesk.one_inventory.order.order", { rows: chosen, supplier }).then((made) => {
      alert(__("{0} purchase orders drafted.", [count(made.length)]));
      picked.value = [];
      if (made.length === 1) go(`/desk/purchase-order/${encodeURIComponent(made[0])}`);
      else go("/desk/purchase-order?docstatus=0");
    });
  const ask = () =>
    chosen.every((one) => one.supplier)
      ? send(null)
      : prompt(
          { fieldtype: "Link", fieldname: "supplier", label: __("Supplier"), options: "Supplier", reqd: 1, description: __("For the lines that have no supplier of their own.") },
          ({ supplier }) => send(supplier),
          __("Who Supplies the Rest?"),
          __("Order")
        );
  if (picked.value.length) ask();
  else confirm(__("Draft purchase orders for all {0} lines?", [count(chosen.length)]), ask);
}

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Reorder") });
  extended(s);
  props.onActions?.(
    [
      s.can.order && lines.value.length && { label: picked.value.length ? __("Order {0}", [count(picked.value.length)]) : __("Order All"), primary: true, onClick: order },
      s.can.request && { label: __("New Material Request"), primary: !s.can.order, button: s.can.order, onClick: () => newDoc("Material Request", { material_request_type: "Purchase" }) },
      { label: __("Material Requests"), onClick: () => go("/desk/material-request") },
      { label: __("Purchase Orders"), onClick: () => go("/desk/purchase-order") },
    ].filter(Boolean)
  );
}
watch(lines, () => said.value && report());

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places_ = onedesk().places;
  if (!places_?.listening("oneinventory_order.shown")) return;
  const f = s.figures;
  const data = { order: { lines: f.lines, requested: f.requested, low: f.low, cost: f.cost, unpriced: f.unpriced } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places_.emit("oneinventory_order.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
