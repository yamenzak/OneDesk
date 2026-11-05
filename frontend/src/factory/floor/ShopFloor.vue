<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures data-tour="onefactory-figures" :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />

      <template v-if="order">
        <div class="mt-6 flex flex-wrap items-start gap-4">
          <Button variant="ghost" icon="lucide-arrow-left" :aria-label="__('All Work Orders')" @click="open(null)" />
          <Avatar :label="order.item_name" :image="order.image" shape="square" size="lg" />
          <div class="min-w-0 flex-1">
            <button type="button" class="truncate rounded-2 text-xl font-semibold text-ink-gray-9 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/item/${encodeURIComponent(order.production_item)}?view=making`)">{{ order.item_name }}</button>
            <div class="mt-0.5 flex flex-wrap gap-x-3 text-base text-ink-gray-5">
              <button type="button" class="hover:underline" @click="go(`/desk/work-order/${encodeURIComponent(order.name)}`)">{{ order.name }}</button>
              <span v-if="order.project_name">{{ order.project_name }}</span>
              <span v-if="order.expected_delivery_date" :class="order.late && 'text-ink-red-4'">{{ order.late ? __("Was expected by {0}", [date(order.expected_delivery_date)]) : __("Expected by {0}", [date(order.expected_delivery_date)]) }}</span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-3">
            <span class="text-base tabular-nums text-ink-gray-7">{{ __("{0} of {1} made", [quantity(order.produced_qty), quantity(order.qty)]) }}</span>
            <Button v-if="order.can_finish > 0 && said.can['Stock Entry']" variant="solid" :label="__('Finish')" @click="onedesk().item.finish(order.name, order.can_finish)" />
          </div>
        </div>
        <Section :title="__('Operations')" icon="lucide-list-ordered" :aside="said.steps.length" class="mt-2">
          <FloorSteps :steps="said.steps" :can="said.can" :employee="said.employee" @changed="load" />
        </Section>
      </template>

      <template v-else>
        <ViewTabs data-tour="onefactory-views" v-model="shown" :views="views" class="mt-5" />
        <FloorSteps v-if="station" :steps="said.steps" :can="said.can" :employee="said.employee" show-order class="mt-4" @changed="load" @open="open" />
        <template v-else>
          <div class="mt-4 flex flex-wrap items-center gap-2">
            <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search Work Orders')" :aria-label="__('Search Work Orders')">
              <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
            </TextInput>
            <span class="ms-auto text-sm tabular-nums text-ink-gray-5">{{ counted }}</span>
          </div>
          <OrderRows :orders="said.work_orders || []" :empty="shown === 'done' ? __('Nothing completed yet') : __('Nothing on the floor')" class="mt-3" @open="open" />
        </template>
      </template>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Button, TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Section, ViewTabs, __, call, count, date, followList, go, newDoc, onResize, onedesk, quantity, setQuery, viewWidth } from "../../kit";
import FloorSteps from "./FloorSteps.vue";
import OrderRows from "./OrderRows.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const focus = ref(props.query.work_order || null);
const shown = ref(props.query.workstation || (props.query.done ? "done" : "open"));
const search = ref("");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

const order = computed(() => (focus.value ? said.value?.work_order : null));
const station = computed(() => !focus.value && !["open", "done"].includes(shown.value));

let asked = 0;
async function load() {
  const mine = ++asked;
  const got = await call("onedesk.one_factory.floor.read", {
    work_order: focus.value,
    workstation: station.value ? shown.value : null,
    done: shown.value === "done" ? 1 : 0,
    search: search.value.trim() || null,
  });
  if (mine !== asked) return;
  said.value = got;
  report();
}

function open(name) {
  focus.value = name;
  setQuery("work_order", name);
  load();
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Job Card", "Work Order", "Employee", "Workstation"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("workstation", ["open", "done"].includes(now) ? null : now);
  setQuery("done", now === "done" ? 1 : null);
  load();
}, { immediate: true });
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});
watch(() => props.query.work_order, (now) => {
  if ((now || null) === focus.value) return;
  focus.value = now || null;
  load();
});

const views = computed(() => [
  { key: "open", label: __("Open"), count: said.value?.figures.open || null },
  { key: "done", label: __("Completed") },
  ...(said.value?.workstations || []).map((one) => ({ key: one.name, label: one.workstation_name || one.name, icon: "lucide-cog" })),
]);

const counted = computed(() => {
  const n = said.value?.total || 0;
  return n === 1 ? __("1 work order") : __("{0} work orders", [count(n)]);
});

const figures = computed(() => {
  const f = said.value.figures;
  return [
    { title: __("Open Work Orders"), value: count(f.open) },
    { title: __("Running Now"), value: count(f.running), note: f.running ? __("Operations with someone on them") : "" },
    { title: __("Waiting to Start"), value: count(f.waiting) },
    { title: __("Closed Today"), value: count(f.done_today) },
  ];
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Shop Floor") });
  extended(s);
  props.onActions?.(
    [
      s.can["Work Order"] && { label: __("New Work Order"), primary: true, onClick: () => newDoc("Work Order") },
      { label: __("Work Orders"), onClick: () => go("/desk/work-order") },
      { label: __("Job Cards"), onClick: () => go("/desk/job-card") },
      { label: __("Workstations"), onClick: () => go("/desk/workstation") },
    ].filter(Boolean)
  );
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("onefactory_floor.shown")) return;
  const data = {
    floor: { ...s.figures, work_order: s.work_order?.name || null, workstation: station.value ? shown.value : null },
  };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("onefactory_floor.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
