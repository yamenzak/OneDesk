<template>
  <!-- OneInventory's Home (one_inventory/page/inventory): what needs somebody
       today, and everything in OneInventory with what it is for
       (one_inventory/home.py). Reports and Setup open their part of it. -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <!-- Today: what needs somebody, kind by kind, the empty kinds left out. -->
      <template v-if="shown === 'today'">
        <p v-if="!parts.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-for="part in parts" :key="part.key" :title="part.title" :icon="part.icon" :aside="part.count" :action="part.action">
          <Rows :rows="part.rows" />
          <button v-if="part.more" type="button" class="mt-2 text-sm text-ink-gray-5 hover:underline" @click="go(part.more.route)">{{ part.more.label }}</button>
        </Section>
      </template>

      <!-- Everything, or one part of it, each with what it is for. -->
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

import { Figures, Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, call, date, followList, go, money, newDoc, onResize, onedesk, quantity, setQuery, viewWidth } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
// Today, everything, or one part of it: /desk/inventory/reports opens Reports.
const shown = ref(props.route[0] || props.query.view || "today");
const search = ref("");
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

async function load() {
  said.value = await call("onedesk.one_inventory.home.read");
  report();
}
load();

// What needs somebody changes with every order, receipt, move and service.
let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Purchase Order", "Purchase Receipt", "Delivery Note", "Stock Entry", "Batch", "Work Order", "Asset Maintenance Log"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => setQuery("view", now === "today" ? null : now));

const views = computed(() => [
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const needed = computed(() => {
  const n = said.value?.needs;
  if (!n) return 0;
  return n.late.count + n.low.count + n.lots.count + n.services.count + n.work.count + n.drafts.length;
});

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.worth !== null && { title: __("Stock Worth"), value: money(f.worth, said.value.currency), route: "/desk/stock-on-hand" },
    { title: __("Running Low"), value: String(f.low), alarm: f.low > 0, route: "/desk/query-report/To Order" },
    { title: __("Late Orders"), value: String(f.late), alarm: f.late > 0 },
    { title: __("Going Off"), value: String(f.going_off), alarm: f.going_off > 0 },
  ].filter(Boolean);
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top", Masters: "lucide-tags" };

function slug(doctype) {
  return doctype.toLowerCase().replace(/ /g, "-");
}

function route(one) {
  if (one.kind === "Report") return `/desk/query-report/${encodeURIComponent(one.target)}`;
  if (one.kind === "Page") return `/desk/${one.target}`;
  if (one.kind === "Masters") return `/desk/masters?type=${encodeURIComponent(one.target)}`;
  return `/desk/${slug(one.target)}`;
}

const groups = computed(() => {
  const words = search.value.trim().toLowerCase();
  const only = ["reports", "setup"].includes(shown.value) ? shown.value : null;
  return said.value.groups
    .filter((group) => !only || group.key === only)
    .map((group) => ({
      ...group,
      rows: said.value.everything.filter(
        (one) => one.group === group.key && (!words || `${one.label} ${one.about}`.toLowerCase().includes(words))
      ),
    }))
    .filter((group) => group.rows.length);
});

// Each kind of thing that needs somebody, as rows, and where the rest are.
const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.late.count)
    out.push({
      key: "late",
      title: __("Late Orders"),
      icon: "lucide-truck",
      count: n.late.count,
      rows: n.late.rows.map((one) => ({
        key: one.order,
        label: one.supplier,
        sub: one.order,
        below: one.items,
        dot: "red",
        value: one.late_by_days === 1 ? __("1 day late") : __("{0} days late", [one.late_by_days]),
        route: `/desk/purchase-order/${encodeURIComponent(one.order)}`,
      })),
      more: more(n.late, __("Purchase Orders"), "/desk/purchase-order?status=To Receive and Bill"),
    });
  if (n.low.count)
    out.push({
      key: "low",
      title: __("Running Low"),
      icon: "lucide-package-minus",
      count: n.low.count,
      action: { text: true, label: __("Order"), icon: "lucide-shopping-cart", onClick: () => go("/desk/query-report/To Order") },
      rows: n.low.rows.map((one) => ({
        key: `${one.item}:${one.warehouse}`,
        label: one.name,
        sub: one.warehouse,
        dot: "orange",
        below: one.on_order ? __("{0} on order", [quantity(one.on_order)]) : __("Nothing on order"),
        value: quantity(one.on_hand),
        under: __("Reorder at {0}", [quantity(one.reorder_level)]),
        route: `/desk/item/${encodeURIComponent(one.item)}?view=stock`,
      })),
      more: more(n.low, __("To Order"), "/desk/query-report/To Order"),
    });
  if (n.lots.count)
    out.push({
      key: "lots",
      title: __("Going Off"),
      icon: "lucide-hourglass",
      count: n.lots.count,
      rows: n.lots.rows.map((one) => ({
        key: one.name,
        label: one.item_name,
        sub: one.batch_id || one.name,
        dot: one.gone ? "red" : "orange",
        value: quantity(one.qty, one.uom),
        under: one.gone ? __("Went off {0}", [date(one.expiry_date)]) : __("Goes off {0}", [date(one.expiry_date)]),
        route: `/desk/batch/${encodeURIComponent(one.name)}`,
      })),
      more: more(n.lots, __("Lots"), "/desk/lots?soon=1"),
    });
  if (n.services.count)
    out.push({
      key: "services",
      title: __("Services Due"),
      icon: "lucide-wrench",
      count: n.services.count,
      rows: n.services.rows.map((one) => ({
        key: one.service,
        label: one.asset,
        sub: one.task,
        dot: one.late ? "red" : "orange",
        below: one.done_by,
        value: one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)]),
        route: `/desk/asset-maintenance-log/${encodeURIComponent(one.service)}`,
      })),
      more: more(n.services, __("Maintenance Log"), "/desk/asset-maintenance-log"),
    });
  if (n.work.count)
    out.push({
      key: "work",
      title: __("Work Running Late"),
      icon: "lucide-factory",
      count: n.work.count,
      rows: n.work.rows.map((one) => ({
        key: one.name,
        label: one.item_name,
        sub: one.name,
        dot: "red",
        value: __("{0} of {1} made", [quantity(one.produced_qty), quantity(one.qty)]),
        under: __("Was wanted by {0}", [date(one.expected_delivery_date)]),
        route: `/desk/floor?work_order=${encodeURIComponent(one.name)}`,
      })),
      more: more(n.work, __("Work Orders"), "/desk/work-order"),
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
  props.onTitle?.({ title: __("OneInventory") });
  extended(s);
  const can = (doctype) => s.everything.some((one) => one.kind === "DocType" && one.target === doctype);
  props.onActions?.(
    [
      can("Item") && { label: __("New Item"), primary: true, onClick: () => newDoc("Item") },
      can("Purchase Receipt") && { label: __("New Receipt"), onClick: () => newDoc("Purchase Receipt") },
      can("Stock Entry") && { label: __("New Move"), onClick: () => newDoc("Stock Entry") },
      can("Material Request") && { label: __("New Material Request"), onClick: () => newDoc("Material Request") },
    ].filter(Boolean)
  );
}

// The page is a place (one_studio/places.py): its extensions are told what
// needs somebody, and may add a note or a button.
const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_home.shown")) return;
  const n = s.needs;
  const data = { home: { ...s.figures, services: n.services.count, work: n.work.count, drafts: n.drafts.reduce((sum, one) => sum + one.count, 0) } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_home.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
