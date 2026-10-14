<template>
  <!-- Sent Out (one_inventory/page/sent_out): work a supplier does on our own
       materials as one page. Each order says what the supplier makes, what
       went to them and what came back, and when it is due, with Send
       Materials and Receive Back where they fit (one_inventory/sent_out.py,
       sent_out_actions.js). Modelled on Katana's outsourced purchase orders
       and Odoo's subcontracting: one table of what is out, and the orders
       not ready to send above it. -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <div class="mt-4">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
      </div>

      <Section v-if="said.to_order.length" :title="__('Not Ready to Send')" icon="lucide-circle-alert" :aside="said.to_order.length" class="mt-4">
        <Rows :rows="toOrder" />
      </Section>
      <div class="mt-3">
        <OutRows :orders="said.orders" :can="said.can" :done="shown === 'done'" :empty="search ? __('No orders match') : shown === 'done' ? __('Nothing back yet') : __('Nothing out now')" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, call, count, date, followList, money, onResize, onedesk, setQuery, viewWidth } from "../kit";
import OutRows from "./OutRows.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.view === "done" ? "done" : "out");
const search = ref("");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

let loads = 0;
async function load() {
  const mine = ++loads;
  const got = await call("onedesk.one_inventory.sent_out.read", { view: shown.value, search: search.value.trim() || null });
  if (mine !== loads) return;
  said.value = got;
  report();
}
load();

let timer = null;
const soonLoad = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
// What the materials with suppliers are worth moves with their bins; a
// project renamed shows too.
const stop = ["Subcontracting Order", "Subcontracting Receipt", "Stock Entry", "Purchase Order", "Bin", "Project"].map((one) => followList(one, soonLoad));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("view", now === "out" ? null : now);
  load();
});
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});

const views = computed(() => [
  { key: "out", label: __("Out Now"), count: said.value?.figures.out || null },
  { key: "done", label: __("Back") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.out !== null && { title: __("Out Now"), value: count(f.out) },
    f.to_send !== null && { title: __("Materials to Send"), value: count(f.to_send), note: f.to_send ? __("Not all sent yet") : "" },
    f.late !== null && { title: __("Late Back"), value: count(f.late), alarm: f.late > 0 },
    f.worth !== null && { title: __("With Suppliers"), value: money(f.worth, said.value.currency), note: __("Our materials, at cost") },
  ].filter(Boolean);
});

// Subcontracted purchase orders that still need their subcontracting order.
const toOrder = computed(() =>
  said.value.to_order.map((one) => ({
    key: one.name,
    label: one.supplier_name || one.supplier,
    sub: one.name,
    below: __("Make its subcontracting order to send the materials"),
    value: one.schedule_date ? __("Due {0}", [date(one.schedule_date)]) : "",
    route: `/desk/purchase-order/${encodeURIComponent(one.name)}`,
    actions: said.value.can.order ? [{ label: __("Make Subcontracting Order"), icon: "lucide-plus", onClick: () => onedesk().sent_out.make_order(one.name) }] : [],
  }))
);

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Sent Out") });
  extended(s);
  props.onActions?.([s.can.order && { label: __("Send Work Out"), primary: true, onClick: () => onedesk().sent_out.new() }].filter(Boolean));
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_sent_out.shown")) return;
  const data = { sent_out: { view: shown.value, ...s.figures } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_sent_out.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
