<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <div v-if="shown !== 'compare'" class="mt-4 flex flex-wrap items-center gap-2">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <TabButtons v-if="shown === 'quotes' && kinds.length > 1" v-model="kind" :options="kinds" class="ms-auto" />
      </div>

      <div v-if="shown === 'asked'" class="mt-3">
        <RequestRows :requests="said.asked" :can="said.can" :empty="search ? __('No requests match') : __('No prices asked for yet')" @compare="compare" />
      </div>
      <div v-else-if="shown === 'quotes'" class="mt-3">
        <QuoteRows :quotes="quotes" :can="said.can" :empty="search || kind !== 'all' ? __('No supplier quotations match') : __('No supplier quotations yet')" @compare="compare" />
      </div>
      <div v-else class="mt-4">
        <div v-if="!said.compare" class="py-3 text-base text-ink-gray-5">{{ __("No supplier quotations to compare yet") }}</div>
        <template v-else>
          <div class="mb-4 flex flex-wrap items-center gap-2">
            <Select v-model="request" class="w-full max-w-md" :options="said.requests.map((one) => ({ value: one.name, label: `${one.label} · ${one.name}` }))" :aria-label="__('Request for Quotation')" />
            <span class="text-sm text-ink-gray-5">{{ asking }}</span>
            <Button class="ms-auto" variant="ghost" icon-right="lucide-arrow-up-right" :label="__('Open Request for Quotation')" @click="go(`/desk/request-for-quotation/${encodeURIComponent(said.compare.name)}`)" />
          </div>
          <QuoteCompare :said="said.compare" :can="said.can" />
        </template>
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, Select, TabButtons, TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, ViewTabs, __, andList, call, count, date, followList, go, onResize, onedesk, setQuery, viewWidth } from "../../kit";
import QuoteCompare from "./QuoteCompare.vue";
import QuoteRows from "./QuoteRows.vue";
import RequestRows from "./RequestRows.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.view || (props.query.request ? "compare" : "asked"));
const search = ref("");
const kind = ref(props.query.kind || "all");
const request = ref(props.query.request || null);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));

let loads = 0;
async function load() {
  const mine = ++loads;
  const got = await call("onedesk.one_inventory.quotes.read", { view: shown.value, search: search.value.trim() || null, request: request.value });
  if (mine !== loads) return;
  said.value = got;
  if (got.compare && request.value !== got.compare.name) request.value = got.compare.name;
  report();
}
load();

let timer = null;
const soonLoad = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Request for Quotation", "Supplier Quotation", "Purchase Order"].map((one) => followList(one, soonLoad));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => {
  setQuery("view", now === "asked" ? null : now);
  load();
});
watch(request, (now, before) => {
  if (!before || now === said.value?.compare?.name) return;
  setQuery("request", now);
  load();
});
let typed = null;
watch(search, () => {
  clearTimeout(typed);
  typed = setTimeout(load, 300);
});

const views = computed(() => [
  { key: "asked", label: __("Request for Quotation") },
  { key: "quotes", label: __("Supplier Quotations") },
  { key: "compare", label: __("Comparison") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  const show = (view, state) => () => {
    kind.value = state || "all";
    shown.value = view;
  };
  return [
    f.waiting !== null && { title: __("Waiting for Prices"), value: count(f.waiting), note: f.waiting ? __("Suppliers still to answer") : "", action: f.waiting ? { icon: "lucide-filter", label: __("Show Requests for Quotation"), onClick: show("asked") } : null },
    f.to_decide !== null && { title: __("Supplier Quotations to Decide"), value: count(f.to_decide), action: f.to_decide ? { icon: "lucide-filter", label: __("Show Supplier Quotations to Decide"), onClick: show("quotes", "decide") } : null },
    f.drafts !== null && { title: __("Draft Supplier Quotations"), value: count(f.drafts), note: f.drafts ? __("Still drafts") : "", action: f.drafts ? { icon: "lucide-filter", label: __("Show Draft Supplier Quotations"), onClick: show("quotes", "check") } : null },
    f.expiring !== null && { title: __("Expiring"), value: count(f.expiring), alarm: f.expiring > 0, note: f.expiring ? __("Within a week") : "", action: f.expiring ? { icon: "lucide-filter", label: __("Show Expiring Supplier Quotations"), onClick: show("quotes", "soon") } : null },
  ].filter(Boolean);
});

const KINDS = {
  decide: (one) => one.status === "Submitted",
  check: (one) => one.status === "Draft",
  soon: (one) => one.expiring,
};
const kinds = computed(() => {
  const all = said.value?.quotes || [];
  const n = (key) => all.filter(KINDS[key]).length;
  return [
    { value: "all", label: __("All") },
    n("decide") && { value: "decide", label: __("To Decide {0}", [count(n("decide"))]) },
    n("check") && { value: "check", label: __("Draft {0}", [count(n("check"))]) },
    n("soon") && { value: "soon", label: __("Expiring {0}", [count(n("soon"))]) },
  ].filter(Boolean);
});
const quotes = computed(() => (kind.value === "all" ? said.value.quotes : said.value.quotes.filter(KINDS[kind.value])));
watch(kind, (now) => setQuery("kind", now === "all" ? null : now));

function compare(name) {
  request.value = name;
  setQuery("request", name);
  if (shown.value === "compare") load();
  else shown.value = "compare";
}

const asking = computed(() => {
  const c = said.value.compare;
  return [c.date ? __("Asked {0}", [date(c.date)]) : "", c.requests.length ? __("From {0}", [andList(c.requests)]) : ""].filter(Boolean).join(" · ");
});
const cheapestOrder = computed(
  () => said.value.can.order && said.value.compare.suppliers.some((one) => one.cheapest_on && !one.draft && !one.expired && ["Submitted", "Partially Ordered"].includes(one.status))
);

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("Request for Quotation") });
  extended(s);
  // On a comparison the thing to do is order the cheapest; asking for
  // prices again waits beside it.
  const ordering = shown.value === "compare" && s.compare && cheapestOrder.value;
  props.onActions?.(
    [
      ordering && { label: __("Order the Cheapest"), primary: true, onClick: () => onedesk().quotes.order_cheapest(s.compare.name, load) },
      s.can.ask && { label: __("Ask for Prices"), primary: !ordering, button: ordering, onClick: () => onedesk().quotes.ask(load) },
    ].filter(Boolean)
  );
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("oneinventory_quotes.shown")) return;
  const data = { quotes: { view: shown.value, request: s.compare?.name || null, ...s.figures } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("oneinventory_quotes.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
