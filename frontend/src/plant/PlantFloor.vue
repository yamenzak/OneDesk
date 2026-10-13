<template>
  <!-- Plant Floor (one_inventory/page/plant): a floor's workstations, each with
       its status and what is running on it, and the stock kept on the floor
       (one_inventory/plant.py, through ERPNext's own Plant Floor). A
       workstation opens its steps on the Shop Floor. -->
  <Page wide>
    <Loading v-if="!said" />
    <div v-else-if="!said.plant" class="py-16 text-center">
      <p class="text-base text-ink-gray-5">{{ __("No plant floors yet") }}</p>
      <Button v-if="said.can['Plant Floor']" class="mt-3" variant="solid" :label="__('New Plant Floor')" @click="newDoc('Plant Floor')" />
    </div>
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-if="said.floors.length > 1" v-model="plant" :views="floors" class="mt-5" />

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <div v-if="said.types.length" class="w-44"><FormControl v-model="type" type="select" :options="typeOptions" :aria-label="__('Type')" /></div>
        <div class="w-44"><FormControl v-model="status" type="select" :options="statusOptions" :aria-label="__('Status')" /></div>
        <span class="ms-auto text-sm tabular-nums text-ink-gray-5">{{ counted }}</span>
      </div>

      <p v-if="!said.workstations.length" class="py-10 text-center text-base text-ink-gray-5">{{ type || status ? __("No workstations match") : __("No workstations on this floor") }}</p>
      <ul v-else class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <li v-for="one in cards" :key="one.name" class="flex flex-col rounded-3 border border-outline-gray-2 bg-surface-cards">
          <button type="button" class="flex flex-1 flex-col gap-2 rounded-3 p-3 text-start hover:bg-surface-gray-1 focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/floor?workstation=${encodeURIComponent(one.name)}`)">
            <div class="flex items-start gap-3">
              <Avatar :label="one.name" :image="one.image" shape="square" size="xl" />
              <div class="min-w-0 flex-1">
                <div class="truncate text-base font-medium text-ink-gray-8">{{ one.name }}</div>
                <div v-if="one.workstation_type" class="truncate text-sm text-ink-gray-5">{{ one.workstation_type }}</div>
                <Badge :label="__(one.status)" :theme="THEMES[one.status] || 'gray'" size="sm" class="mt-1" />
              </div>
            </div>
            <div v-for="step in one.running" :key="step.job_card" class="text-sm text-ink-gray-7">
              <span class="me-1.5 inline-block h-2 w-2 rounded-full bg-surface-green-5" aria-hidden="true" />{{ __("{0} for {1}", [__(step.operation), step.item_name]) }}
              <div v-if="step.people.length" class="ms-3.5 text-ink-gray-5">{{ step.people.join(", ") }}</div>
            </div>
            <div v-if="!one.running.length" class="text-sm text-ink-gray-5">{{ __("Nothing running") }}</div>
            <div v-if="one.waiting" class="text-sm text-ink-gray-5">{{ one.waiting === 1 ? __("1 step waiting") : __("{0} steps waiting", [one.waiting]) }}</div>
          </button>
          <div class="flex items-center justify-end gap-1 border-t border-outline-gray-1 px-2 py-1.5">
            <Button v-if="said.can.Workstation" variant="ghost" size="sm" :label="__('Change Status')" @click="onedesk().plant.status(one.name, one.status, said.statuses, load)" />
            <Button variant="ghost" size="sm" icon="lucide-arrow-up-right" :aria-label="__('Open Workstation')" @click="go(`/desk/workstation/${encodeURIComponent(one.name)}`)" />
          </div>
        </li>
      </ul>

      <Section v-if="said.plant.warehouse" :title="__('Stock Here')" icon="lucide-package" :aside="said.plant.warehouse" class="mt-6">
        <Rows :rows="stock" :empty="__('Nothing kept here')" />
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge, Button, FormControl } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, call, followList, go, newDoc, onResize, onedesk, quantity, setQuery, viewWidth } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const plant = ref(props.query.plant || null);
const type = ref("");
const status = ref("");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

// The colours ERPNext gives each status (workstation.get_color_map).
const THEMES = { Production: "green", Off: "gray", Idle: "gray", Problem: "red", Maintenance: "amber", Setup: "blue" };

let asked = 0;
async function load() {
  const mine = ++asked;
  const got = await call("onedesk.one_inventory.plant.read", { plant: plant.value, workstation_type: type.value || null, status: status.value || null });
  if (mine !== asked) return;
  said.value = got;
  if (got.plant && plant.value !== got.plant.name) plant.value = got.plant.name;
  report();
}

// A status changed anywhere, or a step started or stopped, reads the page again.
let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = [followList("Workstation", soon), followList("Job Card", soon), followList("Plant Floor", soon)];
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(plant, (now, before) => {
  if (before === null && said.value) return;
  setQuery("plant", now);
  load();
});
watch([type, status], load);
load();

const floors = computed(() => (said.value?.floors || []).map((one) => ({ key: one.name, label: one.floor_name || one.name, icon: "lucide-factory" })));
const typeOptions = computed(() => [{ label: __("All Types"), value: "" }, ...said.value.types.map((one) => ({ label: one, value: one }))]);
const statusOptions = computed(() => [{ label: __("Any Status"), value: "" }, ...said.value.statuses.map((one) => ({ label: __(one), value: one }))]);
const cards = computed(() => said.value.workstations);
const counted = computed(() => {
  const n = said.value.workstations.length;
  return n === 1 ? __("1 workstation") : __("{0} workstations", [n]);
});

const figures = computed(() => {
  const f = said.value.figures;
  return [
    { title: __("Workstations"), value: String(f.workstations) },
    { title: __("Making"), value: String(f.making) },
    { title: __("Stopped"), value: String(f.stopped), note: f.stopped ? __("A problem or maintenance") : "" },
    { title: __("Steps Running"), value: String(f.running) },
  ];
});

// What the floor keeps: how much is here, how much of it is kept for work
// orders, and Add Stock or Move Stock as ERPNext's Plant Floor offers them.
const stock = computed(() =>
  said.value.stock.map((one) => ({
    key: one.item_code,
    label: one.item_name,
    avatar: one.item_name,
    image: one.image,
    square: true,
    below: one.for_making ? __("{0} kept for making", [quantity(one.for_making, one.uom)]) : "",
    value: quantity(one.actual_qty, one.uom),
    route: `/desk/item/${encodeURIComponent(one.item_code)}`,
    actions: said.value.can["Stock Entry"]
      ? [
          { label: __("Add Stock"), icon: "lucide-plus", onClick: () => onedesk().plant.stock(said.value.plant, one, "Material Receipt") },
          { label: __("Move Stock"), icon: "lucide-arrow-left-right", onClick: () => onedesk().plant.stock(said.value.plant, one, "Material Transfer") },
        ]
      : [],
  }))
);

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Plant Floor") });
  extended(s);
  props.onActions?.(
    [
      s.can["Plant Floor"] && { label: __("New Plant Floor"), primary: !s.plant, onClick: () => newDoc("Plant Floor") },
      { label: __("Shop Floor"), primary: !!s.plant, onClick: () => go("/desk/floor") },
      s.plant && { label: __("Edit Plant Floor"), onClick: () => go(`/desk/plant-floor/${encodeURIComponent(s.plant.name)}`) },
      { label: __("Workstations"), onClick: () => go("/desk/workstation") },
    ].filter(Boolean)
  );
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_plant.shown")) return;
  const data = { plant: { name: s.plant?.name || null, ...(s.figures || {}), workstations: (s.workstations || []).map((one) => ({ name: one.name, status: one.status })) } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_plant.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
