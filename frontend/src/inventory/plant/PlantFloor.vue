<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else-if="!said.plant" class="py-16 text-center">
      <p class="text-base text-ink-gray-5">{{ __("No plant floors yet") }}</p>
      <Button v-if="said.can['Plant Floor']" class="mt-3" variant="solid" :label="__('New Plant Floor')" @click="newDoc('Plant Floor')" />
    </div>
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-if="said.floors.length > 1" v-model="plant" :views="floors" class="mt-5" />

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <div v-if="said.types.length" class="w-44"><FormControl v-model="type" type="select" :options="typeOptions" :aria-label="__('Type')" /></div>
        <div class="w-44"><FormControl v-model="status" type="select" :options="statusOptions" :aria-label="__('Status')" /></div>
        <span class="ms-auto text-sm tabular-nums text-ink-gray-5">{{ counted }}</span>
      </div>

      <p v-if="!said.workstations.length" class="py-10 text-center text-base text-ink-gray-5">{{ type || status ? __("No workstations match") : __("No workstations on this floor") }}</p>
      <ul v-else class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <li v-for="one in cards" :key="one.name" class="flex flex-col gap-3 rounded-4 border bg-surface-elevation-2 p-4" :class="one.running.length ? 'border-outline-green-2' : 'border-outline-gray-1'">
          <div class="flex items-start gap-3">
            <Avatar :label="one.name" :image="one.image" shape="square" size="xl" />
            <div class="min-w-0 flex-1">
              <button type="button" class="max-w-full truncate rounded-2 text-base font-semibold text-ink-gray-9 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/floor?workstation=${encodeURIComponent(one.name)}`)">{{ one.name }}</button>
              <div v-if="one.workstation_type" class="truncate text-sm text-ink-gray-5">{{ one.workstation_type }}</div>
            </div>
          </div>
          <Dropdown v-if="said.can.Workstation" :options="statusMenu(one)" placement="left">
            <template #trigger>
              <Button size="sm" variant="subtle" class="self-start" icon-right="lucide-chevron-down" :aria-label="__('Change Status')">
                <template #prefix><span class="size-2 rounded-full" :class="DOTS[one.status] || DOTS.Off" aria-hidden="true" /></template>
                {{ __(one.status) }}
              </Button>
            </template>
          </Dropdown>
          <Badge v-else class="self-start" :label="__(one.status)" :theme="THEMES[one.status] || 'gray'" size="md" />

          <div v-for="step in one.running" :key="step.job_card" class="min-w-0">
            <div class="truncate text-sm font-medium text-ink-gray-8">{{ __("{0} for {1}", [__(step.operation), step.item_name]) }}</div>
            <div class="flex items-baseline justify-between gap-3">
              <span class="truncate text-sm text-ink-gray-5">{{ step.people.join(", ") }}</span>
              <span v-if="step.since" class="shrink-0 text-lg font-semibold tabular-nums text-ink-green-4">{{ clock(step.since) }}</span>
            </div>
          </div>
          <div v-if="!one.running.length" class="text-sm text-ink-gray-5">{{ __("Nothing running") }}</div>

          <div class="mt-auto flex items-center justify-between gap-2 border-t border-outline-gray-1 pt-3">
            <span class="text-sm text-ink-gray-5">{{ one.waiting ? (one.waiting === 1 ? __("1 operation waiting") : __("{0} operations waiting", [count(one.waiting)])) : __("Nothing waiting") }}</span>
            <div class="flex items-center gap-1">
              <Button size="sm" variant="ghost" :label="__('Operations')" icon-right="lucide-arrow-right" @click="go(`/desk/floor?workstation=${encodeURIComponent(one.name)}`)" />
              <Button size="sm" variant="ghost" icon="lucide-settings-2" :aria-label="__('Open Workstation')" @click="go(`/desk/workstation/${encodeURIComponent(one.name)}`)" />
            </div>
          </div>
        </li>
      </ul>

      <Section v-if="said.plant.warehouse" :title="__('Stock Here')" icon="lucide-package" :aside="said.plant.place || said.plant.warehouse" class="mt-6">
        <p v-if="!said.stock.length" class="py-3 text-base text-ink-gray-5">{{ __("Nothing kept here") }}</p>
        <List v-else :columns="stockColumns" divider="full" :row-height="52" class="-mx-3 list-gap-4 list-row-px-3">
          <ListHeader>
            <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end">{{ __("Actual Qty") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Reserved Qty for Production") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end max-lg:hidden">{{ __("Coming") }}</ListHeaderCell>
            <ListHeaderCell />
          </ListHeader>
          <ListRows :items="said.stock" row-key="item_code" v-slot="{ item }">
            <ListRow @click="go(`/desk/item/${encodeURIComponent(item.item_code)}?view=stock`)">
              <ListCell class="min-w-0 gap-3">
                <Avatar :label="item.item_name" :image="item.image" shape="square" size="md" />
                <span class="truncate text-base text-ink-gray-8">{{ item.item_name }}</span>
              </ListCell>
              <ListCell v-for="key in ['actual_qty', 'for_making', 'coming']" :key="key" class="justify-end whitespace-nowrap tabular-nums" :class="STOCK_SHOWN[key]">
                <template v-if="item[key]">
                  <span class="text-base" :class="key === 'actual_qty' ? 'text-ink-gray-8' : 'text-ink-gray-7'">{{ quantity(item[key]) }}</span>
                  <span class="ms-1 text-sm text-ink-gray-5">{{ __(item.unit) }}</span>
                </template>
                <span v-else class="text-base text-ink-gray-4">–</span>
              </ListCell>
              <ListCell class="justify-end" @click.stop>
                <Dropdown v-if="said.can['Stock Entry']" :options="stockMenu(item)" placement="right">
                  <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
                </Dropdown>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown, FormControl } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Page, PlaceSpot, Section, ViewTabs, __, call, count, duration, followList, go, newDoc, onResize, onedesk, quantity, secondsSince, setQuery, setValue, viewWidth } from "../../kit";

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

const THEMES = { Production: "green", Off: "gray", Idle: "gray", Problem: "red", Maintenance: "amber", Setup: "blue" };
const DOTS = { Production: "bg-surface-green-5", Off: "bg-surface-gray-5", Idle: "bg-surface-gray-4", Problem: "bg-surface-red-5", Maintenance: "bg-surface-amber-5", Setup: "bg-surface-blue-5" };
const stockColumns = { base: ["minmax(0,1fr)", "auto", "2rem"], sm: ["minmax(0,1fr)", "8rem", "8rem", "2rem"], lg: ["minmax(0,1fr)", "8rem", "8rem", "8rem", "2rem"] };
const STOCK_SHOWN = { actual_qty: "", for_making: "max-sm:hidden", coming: "max-lg:hidden" };

const now = ref(Date.now());
const tick = setInterval(() => (now.value = Date.now()), 1000);
onBeforeUnmount(() => clearInterval(tick));
const clock = (since) => (now.value, duration(secondsSince(since)));

const statusMenu = (one) =>
  said.value.statuses.map((value) => ({
    label: __(value),
    icon: value === one.status ? "lucide-check" : undefined,
    onClick: () => value !== one.status && setValue("Workstation", one.name, "status", value).then(load),
  }));
const stockMenu = (one) => [
  { label: __("Add Stock"), icon: "lucide-plus", onClick: () => onedesk().plant.stock(said.value.plant, one, "Material Receipt") },
  { label: __("Move Stock"), icon: "lucide-arrow-left-right", onClick: () => onedesk().plant.stock(said.value.plant, one, "Material Transfer") },
];

let asked = 0;
async function load() {
  const mine = ++asked;
  const got = await call("onedesk.one_inventory.plant.read", { plant: plant.value, workstation_type: type.value || null, status: status.value || null });
  if (mine !== asked) return;
  said.value = got;
  if (got.plant && plant.value !== got.plant.name) plant.value = got.plant.name;
  report();
}

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
  return n === 1 ? __("1 workstation") : __("{0} workstations", [count(n)]);
});

const figures = computed(() => {
  const f = said.value.figures;
  return [
    { title: __("Workstations"), value: count(f.workstations) },
    { title: __("Production"), value: count(f.making), action: f.making ? { icon: "lucide-filter", label: __("Show Workstations in Production"), onClick: () => (status.value = "Production") } : null },
    { title: __("Stopped"), value: count(f.stopped), alarm: f.stopped > 0, note: f.stopped ? __("A problem or maintenance") : "" },
    { title: __("Operations Running"), value: count(f.running) },
  ];
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Plant Floor") });
  extended(s);
  props.onActions?.(
    [
      s.can["Plant Floor"] && { label: __("New Plant Floor"), primary: !s.plant, onClick: () => newDoc("Plant Floor") },
      s.plant && s.can["New Workstation"] && { label: __("New Workstation"), primary: true, onClick: () => newDoc("Workstation", { plant_floor: s.plant.name }) },
      { label: __("Shop Floor"), onClick: () => go("/desk/floor") },
      s.plant && { label: __("Edit Plant Floor"), onClick: () => go(`/desk/plant-floor/${encodeURIComponent(s.plant.name)}`) },
      { label: __("Workstations"), onClick: () => go("/desk/workstation") },
    ].filter(Boolean)
  );
}

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
