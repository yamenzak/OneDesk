<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="cards.length" data-tour="onefactory-figures" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5 [&_.truncate]:whitespace-normal">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" data-tour="onefactory-home-views" />

      <template v-if="shown === 'today'">
        <p v-if="!parts.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-for="part in parts" :key="part.key" :title="part.title" :icon="part.icon" :aside="part.count" :action="part.action">
          <Rows :rows="part.rows" />
          <button v-if="part.more" type="button" class="mt-2 text-sm text-ink-gray-5 hover:underline" @click="go(part.more.route)">{{ part.more.label }}</button>
        </Section>
      </template>

      <template v-else>
        <TextInput v-model="search" class="mt-4 w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <p v-if="!groups.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing matches") }}</p>
        <Section v-for="group in groups" :key="group.key" :title="group.label" :aside="group.rows.length">
          <ul class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 xl:grid-cols-3">
            <li v-for="one in group.rows" :key="one.target">
              <button type="button" class="flex w-full items-start gap-3 rounded-3 px-2 py-2.5 text-start hover:bg-surface-gray-2 focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(route(one))">
                <span :class="ICONS[one.kind]" class="mt-0.5 size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
                <span class="min-w-0">
                  <span class="block truncate text-base text-ink-gray-8">{{ one.label }}</span>
                  <span class="block text-sm text-ink-gray-5">{{ one.about }}</span>
                </span>
              </button>
            </li>
          </ul>
        </Section>
      </template>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { TextInput } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";

import { Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, call, count, date, followList, go, money, newDoc, onedesk, quantity, setQuery } from "../../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const wanted = () => props.query.view || props.route[0] || "today";
const shown = ref(wanted());
watch(
  () => [props.route[0], props.query.view],
  () => wanted() !== shown.value && (shown.value = wanted())
);
const search = ref("");

async function load() {
  said.value = await call("onedesk.one_factory.home.read");
  report();
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Work Order", "Job Card", "BOM", "Production Plan", "Subcontracting Order", "Subcontracting Receipt", "Stock Entry"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => setQuery("view", now === (props.route[0] || "today") ? null : now));

const views = computed(() => [
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key) && said.value.everything.some((row) => row.group === one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const needed = computed(() => {
  const n = said.value?.needs;
  if (!n) return 0;
  return n.late.count + n.start.count + n.back.count + n.drafts.length;
});

const CARDS = () => [
  { key: "open", title: __("Open Work Orders"), route: "/desk/floor" },
  { key: "running", title: __("Steps Running Now"), route: "/desk/job-card?status=Work In Progress" },
  { key: "late", title: __("Late Work Orders"), route: `/desk/work-order?docstatus=1&status=${encodeURIComponent(JSON.stringify(["in", ["Not Started", "In Process"]]))}&expected_delivery_date=${encodeURIComponent(JSON.stringify(["<", said.value.today]))}` },
  { key: "out", title: __("Out with Suppliers"), route: "/desk/subcontracting-order?docstatus=1" },
  { key: "made", title: __("Made This Month"), money: true, route: "/desk/stock-entry?purpose=Manufacture&docstatus=1" },
];
const cards = computed(() => {
  const got = said.value?.figures || {};
  return CARDS()
    .filter((one) => got[one.key] !== null && got[one.key] !== undefined)
    .map((one) => ({
      key: one.key,
      route: one.route,
      props: { title: one.title, value: got[one.key] ?? 0, format: one.money ? (value) => money(value, said.value.currency, 0) : count },
    }));
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top" };

function slug(doctype) {
  return doctype.toLowerCase().replace(/ /g, "-");
}

function route(one) {
  if (one.kind === "Report") return `/desk/query-report/${encodeURIComponent(one.target)}`;
  if (one.kind === "Page") return `/desk/${one.target}`;
  return `/desk/${slug(one.target)}`;
}

const groups = computed(() => {
  const words = search.value.trim().toLowerCase();
  const matches = (one) => !words || `${one.label} ${one.about}`.toLowerCase().includes(words);
  const only = ["reports", "setup"].includes(shown.value) ? shown.value : null;
  return said.value.groups
    .filter((group) => !only || group.key === only)
    .map((group) => ({ ...group, rows: said.value.everything.filter((one) => one.group === group.key && matches(one)) }))
    .filter((group) => group.rows.length);
});

const made = (one) => __("{0} of {1} made", [quantity(one.produced_qty), quantity(one.qty, one.stock_uom)]);
const order = (one) => `/desk/work-order/${encodeURIComponent(one.name)}`;

const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.late.count)
    out.push({
      key: "late",
      title: __("Late Work Orders"),
      icon: "lucide-clock-alert",
      count: n.late.count,
      rows: n.late.rows.map((one) => ({
        key: one.name,
        label: one.item_name || one.production_item,
        sub: one.name,
        dot: "red",
        below: made(one),
        value: one.late_by === 1 ? __("1 day late") : __("{0} days late", [one.late_by]),
        under: __("Wanted {0}", [date(one.expected_delivery_date)]),
        route: order(one),
      })),
      more: more(n.late, __("Work Order"), "/desk/work-order?docstatus=1"),
    });
  if (n.start.count)
    out.push({
      key: "start",
      title: __("Due to Start"),
      icon: "lucide-play",
      count: n.start.count,
      action: { text: true, label: __("Shop Floor"), icon: "lucide-hard-hat", onClick: () => go("/desk/floor") },
      rows: n.start.rows.map((one) => ({
        key: one.name,
        label: one.item_name || one.production_item,
        sub: one.name,
        dot: "amber",
        below: quantity(one.qty, one.stock_uom),
        value: __("Planned {0}", [date(one.planned_start_date)]),
        route: order(one),
      })),
      more: more(n.start, __("Work Order"), "/desk/work-order?status=Not Started"),
    });
  if (n.back.count)
    out.push({
      key: "back",
      title: __("Late Back from Suppliers"),
      icon: "lucide-truck",
      count: n.back.count,
      rows: n.back.rows.map((one) => ({
        key: one.name,
        label: one.supplier_name || one.supplier,
        sub: one.name,
        dot: "red",
        below: one.makes.map((made) => made.name).join(", "),
        value: __("Due {0}", [date(one.schedule_date)]),
        route: `/desk/subcontracting-order/${encodeURIComponent(one.name)}`,
      })),
      more: more(n.back, __("Subcontracting Order"), "/desk/subcontracting-order?docstatus=1"),
    });
  if (n.drafts.length)
    out.push({
      key: "drafts",
      title: __("Left as Drafts"),
      icon: "lucide-file-pen-line",
      count: n.drafts.reduce((sum, one) => sum + one.count, 0),
      rows: n.drafts.map((one) => ({
        key: one.doctype,
        label: one.label,
        below: __("Started more than a day ago"),
        value: one.count === 1 ? __("1 draft") : __("{0} drafts", [one.count]),
        route: `/desk/${slug(one.doctype)}?docstatus=0`,
      })),
    });
  return out;
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("OneFactory") });
  extended(s);
  const can = (doctype) => (s.may_make || []).includes(doctype);
  const made = [
    can("Work Order") && { label: __("New Work Order"), onClick: () => newDoc("Work Order") },
    can("BOM") && { label: __("New BOM"), onClick: () => newDoc("BOM") },
    can("Production Plan") && { label: __("New Production Plan"), onClick: () => newDoc("Production Plan") },
  ].filter(Boolean);
  if (made.length) made[0].primary = true;
  props.onActions?.(made);
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("onefactory_home.shown")) return;
  const n = s.needs;
  const data = { home: { late: n.late.count, start: n.start.count, back: n.back.count, drafts: n.drafts.reduce((sum, one) => sum + one.count, 0) } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("onefactory_home.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
