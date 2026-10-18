<template>
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
      <div class="mt-3">
        <UpkeepRows :kind="shown" :rows="rows" :can="said.can" :currency="said.currency" :empty="empty" @changed="load" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, ViewTabs, __, call, count, followList, money, onResize, onedesk, setQuery, viewWidth } from "../kit";
import UpkeepRows from "./UpkeepRows.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const VIEWS = ["due", "repairs", "plans", "log"];
const said = ref(null);
const shown = ref(VIEWS.includes(props.query.view) ? props.query.view : "due");
const search = ref("");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

let loads = 0;
async function load() {
  const mine = ++loads;
  const got = await call("onedesk.one_inventory.upkeep.read", { view: shown.value, search: search.value.trim() || null });
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
const stop = ["Asset Maintenance Log", "Asset Maintenance", "Asset Repair", "Asset"].map((one) => followList(one, soonLoad));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("view", now === "due" ? null : now);
  load();
});
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});

const views = computed(() => [
  { key: "due", label: __("Planned"), count: (said.value?.figures.late || 0) + (said.value?.figures.this_week || 0) || null },
  { key: "repairs", label: __("Asset Repair"), count: said.value?.figures.broken || null },
  { key: "plans", label: __("Asset Maintenance") },
  { key: "log", label: __("Completed") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.this_week !== null && { title: __("Due This Week"), value: count(f.this_week) },
    f.late !== null && { title: __("Overdue"), value: count(f.late), alarm: f.late > 0, action: f.late ? { icon: "lucide-filter", label: __("Show Planned"), onClick: () => (shown.value = "due") } : null },
    f.broken !== null && { title: __("Out of Order"), value: count(f.broken), alarm: f.broken > 0, action: f.broken ? { icon: "lucide-filter", label: __("Show Asset Repairs"), onClick: () => (shown.value = "repairs") } : null },
    f.repairs_cost !== null && { title: __("Repair Cost"), value: money(f.repairs_cost, said.value.currency), note: __("Last twelve months") },
  ].filter(Boolean);
});

const empty = computed(
  () =>
    ({
      due: __("Nothing due"),
      repairs: __("Nothing broken"),
      plans: __("No Asset Maintenance yet"),
      log: __("Nothing completed yet"),
    })[shown.value]
);

const rows = computed(() => said.value[shown.value] || []);

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Asset Maintenance") });
  extended(s);
  props.onActions?.(
    [
      s.can.repair && { label: __("New Asset Repair"), primary: true, onClick: () => onedesk().upkeep.broken() },
      s.can.plan && { label: __("New Asset Maintenance"), onClick: () => onedesk().upkeep.plan() },
    ].filter(Boolean)
  );
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_upkeep.shown")) return;
  const data = { upkeep: { view: shown.value, ...s.figures } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_upkeep.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
