<template>
  <!-- OneInventory's Home (one_inventory/page/inventory): what needs somebody
       today, and everything in OneInventory with what it is for
       (one_inventory/home.py). Reports and Setup open their part of it. -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <!-- The headline figures, each with its months as a sparkline. -->
      <div v-if="cards.length" ref="cardsRoot" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <!-- Overview: what needs somebody, then the story of the stock. -->
      <template v-if="shown === 'overview'">
        <Loading v-if="!story" />
        <InventoryStory v-else :story="story" :needs="chips" @today="shown = 'today'" />
      </template>

      <!-- Today: what needs somebody, kind by kind, the empty kinds left out. -->
      <template v-else-if="shown === 'today'">
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
import { NumberCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, call, count, date, followList, go, money, newDoc, onedesk, quantity, setQuery } from "../kit";
import InventoryStory from "./InventoryStory.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
// Today, everything, or one part of it: /desk/inventory/reports opens Reports.
const shown = ref(props.route[0] || props.query.view || "overview");
const search = ref("");
// The story is read beside what needs somebody, so Today never waits on it.
const story = ref(null);

async function load() {
  call("onedesk.one_inventory.story.read").then((got) => (story.value = got));
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
watch(shown, (now) => setQuery("view", now === "overview" ? null : now));

const views = computed(() => [
  { key: "overview", label: __("Overview") },
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const needed = computed(() => {
  const n = said.value?.needs;
  if (!n) return 0;
  return n.late.count + n.low.count + n.lots.count + n.services.count + n.work.count + n.drafts.length;
});

// The headline figures: what stock is worth, what came in, went out and was
// made this month, what is still on order and how many papers moved stock,
// each against last month and drawn over its months. Still on Order is drawn
// over what was ordered each month, which is not what it counts, so it is
// not set against last month (`alone`).
const CARDS = () => [
  { key: "worth", title: __("Stock Worth"), money: true, type: "area", hue: 0, route: "/desk/stock-on-hand" },
  { key: "taken_in", title: __("Taken In This Month"), money: true, type: "bar", hue: 2, route: "/desk/purchase-receipt" },
  { key: "sent_out", title: __("Sent Out This Month"), money: true, type: "bar", hue: 6, route: "/desk/delivery-note" },
  { key: "made", title: __("Made This Month"), money: true, type: "line", hue: 4, route: "/desk/work-order" },
  { key: "on_order", title: __("Still on Order"), money: true, type: "area", hue: 5, alone: true, route: "/desk/purchase-order?status=To Receive and Bill" },
  { key: "papers", title: __("Moves This Month"), type: "bar", hue: 1, route: "/desk/query-report/Stock Ledger" },
];
// The cards' colours, as frappe-ui reads them for this island and its theme.
const cardsRoot = ref();
const { tokens } = useChartTokens(cardsRoot);
const change = (series) => {
  const [before, now] = series.slice(-2);
  return before ? Math.round(((now - before) / Math.abs(before)) * 100) : null;
};
const cards = computed(() => {
  const got = story.value?.cards || {};
  const hues = tokens.value.categorical;
  return CARDS()
    .filter((one) => got[one.key])
    .map((one) => ({
      key: one.key,
      route: one.route,
      props: {
        title: one.title,
        value: got[one.key].value ?? 0,
        format: one.money ? (value) => money(value, story.value.currency, 0) : count,
        ...(one.alone || change(got[one.key].series) === null ? {} : { delta: change(got[one.key].series), deltaSuffix: "%", deltaCaption: __("vs last month") }),
        sparkline: { data: got[one.key].series, type: one.type, color: hues[one.hue] || undefined },
      },
    }));
});

// What needs somebody, one button each, leading to Today.
const chips = computed(() => {
  const n = said.value?.needs;
  if (!n) return [];
  const drafts = n.drafts.reduce((sum, d) => sum + d.count, 0);
  return [
    n.late.count && { key: "late", tone: "late", icon: "lucide-truck", label: n.late.count === 1 ? __("1 Late Order") : __("{0} Late Orders", [n.late.count]) },
    n.low.count && { key: "low", tone: "soon", icon: "lucide-package-minus", label: n.low.count === 1 ? __("1 Item Running Low") : __("{0} Items Running Low", [n.low.count]) },
    n.lots.count && { key: "lots", tone: "soon", icon: "lucide-hourglass", label: n.lots.count === 1 ? __("1 Lot Going Off") : __("{0} Lots Going Off", [n.lots.count]) },
    n.services.count && { key: "services", tone: "soon", icon: "lucide-wrench", label: n.services.count === 1 ? __("1 Service Due") : __("{0} Services Due", [n.services.count]) },
    n.work.count && { key: "work", tone: "late", icon: "lucide-factory", label: n.work.count === 1 ? __("1 Work Order Late") : __("{0} Work Orders Late", [n.work.count]) },
    n.drafts.length && { key: "drafts", tone: "left", icon: "lucide-file-pen-line", label: drafts === 1 ? __("1 Draft Left") : __("{0} Drafts Left", [drafts]) },
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
  const matches = (one) => !words || `${one.label} ${one.about}`.toLowerCase().includes(words);
  // Reports and Setup set out by what each part is about, a section to a
  // topic, as Zoho Inventory's Reports Center and Odoo's configuration do.
  const sections = said.value.sections?.[shown.value];
  if (sections)
    return sections
      .map((topic) => ({ ...topic, rows: said.value.everything.filter((one) => one.group === shown.value && one.topic === topic.key && matches(one)) }))
      .filter((topic) => topic.rows.length);
  return said.value.groups
    .map((group) => ({
      ...group,
      rows: said.value.everything.filter(
        (one) => one.group === group.key && matches(one)
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
      action: { text: true, label: __("Order"), icon: "lucide-shopping-cart", onClick: () => go("/desk/to-order") },
      rows: n.low.rows.map((one) => ({
        key: `${one.item}:${one.warehouse}`,
        label: one.name,
        sub: one.warehouse,
        dot: "amber",
        below: one.on_order ? __("{0} on order", [quantity(one.on_order)]) : __("Nothing on order"),
        value: quantity(one.on_hand),
        under: __("Reorder at {0}", [quantity(one.reorder_level)]),
        route: `/desk/item/${encodeURIComponent(one.item)}?view=stock`,
      })),
      more: more(n.low, __("To Order"), "/desk/to-order"),
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
        dot: one.gone ? "red" : "amber",
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
        dot: one.late ? "red" : "amber",
        below: one.done_by,
        value: one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)]),
        route: `/desk/asset-maintenance-log/${encodeURIComponent(one.service)}`,
      })),
      more: more(n.services, __("Upkeep"), "/desk/upkeep"),
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
