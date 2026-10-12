<template>
  <!-- Upkeep (one_inventory/page/upkeep): servicing and mending the company's
       equipment as one page. Due lists the services not done yet, Repairs
       what broke, Plans each asset's servicing, and Done what was done
       (one_inventory/upkeep.py, upkeep_actions.js). -->
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
        <Rows :rows="rows" :empty="empty" />
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, ViewTabs, __, call, date, followList, go, money, onResize, onedesk, setQuery, viewWidth } from "../kit";

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
const stop = ["Asset Maintenance Log", "Asset Maintenance", "Asset Repair"].map((one) => followList(one, soonLoad));
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
  { key: "due", label: __("Due"), count: (said.value?.figures.late || 0) + (said.value?.figures.this_week || 0) || null },
  { key: "repairs", label: __("Repairs"), count: said.value?.figures.broken || null },
  { key: "plans", label: __("Plans") },
  { key: "log", label: __("Done") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.this_week !== null && { title: __("Due This Week"), value: String(f.this_week) },
    f.late !== null && { title: __("Late"), value: String(f.late), alarm: f.late > 0 },
    f.broken !== null && { title: __("Out of Order"), value: String(f.broken), alarm: f.broken > 0 },
    f.repairs_cost !== null && { title: __("Repairs Cost"), value: money(f.repairs_cost, said.value.currency), note: __("Last twelve months") },
  ].filter(Boolean);
});

const empty = computed(
  () =>
    ({
      due: __("Nothing due"),
      repairs: __("Nothing broken"),
      plans: __("No equipment is serviced on a plan yet"),
      log: __("Nothing done yet"),
    })[shown.value]
);

const rows = computed(() => {
  const s = said.value;
  if (shown.value === "repairs") return s.repairs.map(repair);
  if (shown.value === "plans") return s.plans.map(plan);
  if (shown.value === "log") return s.log.map(entry);
  return s.due.map(service);
});

// A service not done yet: the asset, the job and who does it, when it is
// due, red once late.
function service(one) {
  return {
    key: one.name,
    label: one.asset_name,
    sub: one.task_name,
    avatar: one.asset_name,
    image: one.image,
    square: true,
    dot: one.late ? "red" : null,
    badge: one.late ? { label: __("Late"), theme: "red" } : null,
    below: [one.assign_to_name, __(one.periodicity || "")].filter(Boolean).join(" · "),
    value: one.due_date ? __("Due {0}", [date(one.due_date)]) : "",
    route: `/desk/asset-maintenance-log/${encodeURIComponent(one.name)}`,
    actions: [
      said.value.can.done && { label: __("Mark Done"), icon: "lucide-check", onClick: () => onedesk().upkeep.done(one.name, one.asset_name, load) },
      { label: __("Open Asset"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/asset/${encodeURIComponent(one.asset)}`) },
    ].filter(Boolean),
  };
}

// A repair: what is wrong, how long it has been out of use, and its cost.
function repair(one) {
  return {
    key: one.name,
    label: one.asset_name,
    sub: one.name,
    avatar: one.asset_name,
    image: one.image,
    square: true,
    badge: one.open ? { label: __("Out of Order"), theme: "red" } : { label: __("Mended"), theme: "green" },
    below: one.description || "",
    value: one.open ? __("Out {0} days", [one.days_out ?? 0]) : money(one.repair_cost, said.value.currency),
    under: one.failure_date ? __("Broke {0}", [date(one.failure_date.slice(0, 10))]) : "",
    route: `/desk/asset-repair/${encodeURIComponent(one.name)}`,
  };
}

// An asset's plan: its jobs, how often, and when each is next due.
function plan(one) {
  return {
    key: one.name,
    label: one.asset_name,
    sub: one.team,
    avatar: one.asset_name,
    image: one.image,
    square: true,
    lines: one.tasks.map((job) => [job.task, __(job.periodicity || ""), job.by].filter(Boolean).join(" · ")),
    value: one.next ? __("Next {0}", [date(one.next)]) : "",
    under: one.manager ? __("Managed by {0}", [one.manager]) : "",
    route: `/desk/asset-maintenance/${encodeURIComponent(one.name)}`,
  };
}

// What was done: a service with who did it, or a repair with what it cost.
function entry(one) {
  const repaired = one.kind === "repair";
  return {
    key: one.name,
    label: one.asset_name,
    sub: one.what,
    icon: repaired ? "lucide-wrench" : "lucide-check",
    below: repaired ? "" : [one.by, one.notes].filter(Boolean).join(" · "),
    value: repaired ? money(one.cost, said.value.currency) : "",
    under: one.on ? date(one.on) : "",
    route: repaired ? `/desk/asset-repair/${encodeURIComponent(one.name)}` : `/desk/asset-maintenance-log/${encodeURIComponent(one.name)}`,
  };
}

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Upkeep") });
  extended(s);
  props.onActions?.(
    [
      s.can.repair && { label: __("Report a Breakdown"), primary: true, onClick: () => onedesk().upkeep.broken() },
      s.can.plan && { label: __("Plan a Service"), onClick: () => onedesk().upkeep.plan() },
    ].filter(Boolean)
  );
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
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
