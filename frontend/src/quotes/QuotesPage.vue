<template>
  <!-- Quotes (one_inventory/page/quotes): asking suppliers for prices, their
       answers and the comparison as one page. Asked lists each request with
       who answered, Quotes each supplier's quote, and Compare one request's
       quotes side by side with the orders (one_inventory/quotes.py,
       quotes_actions.js). -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Figures :figures="figures" :columns="figures.length" :boxed="wide" class="mt-6" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <div v-if="shown !== 'compare'" class="mt-4">
        <TextInput v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
      </div>

      <div v-if="shown === 'asked'" class="mt-3">
        <Rows :rows="asked" :empty="search ? __('No requests match') : __('No prices asked for yet')" />
      </div>
      <div v-else-if="shown === 'quotes'" class="mt-3">
        <Rows :rows="quotes" :empty="search ? __('No quotes match') : __('No quotes yet')" />
      </div>
      <div v-else class="mt-4">
        <div v-if="!said.compare" class="py-3 text-base text-ink-gray-5">{{ __("No quotes to compare yet") }}</div>
        <template v-else>
          <div class="mb-4 flex flex-wrap items-center gap-2">
            <Select v-model="request" class="w-full max-w-sm" :options="said.requests.map((one) => ({ value: one.name, label: `${one.label} · ${one.name}` }))" :aria-label="__('Request')" />
            <span class="text-sm text-ink-gray-5">{{ asking }}</span>
            <Button v-if="cheapestOrder" class="ms-auto" variant="solid" :label="__('Order the Cheapest')" @click="onedesk().quotes.order_cheapest(said.compare.name, load)" />
            <Button :class="{ 'ms-auto': !cheapestOrder }" variant="ghost" icon-right="lucide-arrow-up-right" :label="__('Open Request')" @click="go(`/desk/request-for-quotation/${encodeURIComponent(said.compare.name)}`)" />
          </div>
          <QuoteCompare :said="said.compare" :can="said.can" />
        </template>
      </div>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, Select, TextInput } from "frappe-ui";

import { Figures, Loading, Page, PlaceSpot, Rows, ViewTabs, __, andList, call, date, followList, go, money, onResize, onedesk, setQuery, viewWidth } from "../kit";
import QuoteCompare from "./QuoteCompare.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.query.view || (props.query.request ? "compare" : "asked"));
const search = ref("");
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
  { key: "asked", label: __("Asked"), count: said.value?.figures.waiting || null },
  { key: "quotes", label: __("Quotes"), count: said.value?.figures.to_decide || null },
  { key: "compare", label: __("Compare") },
]);

const figures = computed(() => {
  const f = said.value.figures;
  return [
    f.waiting !== null && { title: __("Waiting for Prices"), value: String(f.waiting), note: f.waiting ? __("Suppliers still to answer") : "" },
    f.to_decide !== null && { title: __("Quotes to Decide"), value: String(f.to_decide) },
    f.drafts !== null && { title: __("Quotes to Check"), value: String(f.drafts), note: f.drafts ? __("Still drafts") : "" },
    f.expiring !== null && { title: __("Running Out"), value: String(f.expiring), alarm: f.expiring > 0, note: f.expiring ? __("Within a week") : "" },
  ].filter(Boolean);
});

// A request in a line: what it asks for, who answered and who has not yet.
const asked = computed(() =>
  said.value.asked.map((one) => {
    const waiting = one.suppliers.filter((row) => !row.answered);
    const answered = one.suppliers.filter((row) => row.answered);
    return {
      key: one.name,
      label: one.what,
      sub: one.name,
      badge: badge(one, waiting),
      lines: [
        answered.length ? __("Answered by {0}", [andList(answered.map((row) => row.name))]) : "",
        waiting.length && !one.draft ? __("Waiting for {0}", [andList(waiting.map((row) => row.name))]) : "",
      ].filter(Boolean),
      value: __("{0} of {1}", [one.answered, one.suppliers.length]),
      under: one.date ? __("Asked {0}", [date(one.date)]) : "",
      onClick: () => compare(one.name),
      actions: [
        one.answered && { label: __("Compare"), icon: "lucide-columns-3", onClick: () => compare(one.name) },
        ...(said.value.can.quote && !one.draft ? waiting.map((row) => ({ label: __("Add Quote from {0}", [row.name]), icon: "lucide-plus", onClick: () => onedesk().quotes.add(one.name, row.supplier) })) : []),
        { label: __("Open Request"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/request-for-quotation/${encodeURIComponent(one.name)}`) },
      ].filter(Boolean),
    };
  })
);

function badge(one, waiting) {
  if (one.draft) return { label: __("Draft"), theme: "gray" };
  if (one.ordered) return { label: __("Ordered"), theme: "green" };
  if (waiting.length) return { label: __("Waiting"), theme: "amber" };
  return { label: __("Answered"), theme: "blue" };
}

const STATES = {
  Draft: [() => __("To Check"), "gray"],
  Submitted: [() => __("To Decide"), "blue"],
  "Partially Ordered": [() => __("Partly Ordered"), "green"],
  Ordered: [() => __("Ordered"), "green"],
  Expired: [() => __("Expired"), "red"],
  Stopped: [() => __("Stopped"), "gray"],
};

// A supplier's quote in a line: its total in its own money, until when it
// holds, and what it answers or was ordered as.
const quotes = computed(() =>
  said.value.quotes.map((one) => {
    const [label, theme] = STATES[one.status] || [() => __(one.status), "gray"];
    return {
      key: one.name,
      label: one.supplier_name || one.supplier,
      sub: one.name,
      dot: one.expiring ? "amber" : null,
      badge: { label: label(), theme },
      below: [
        one.request ? __("Answers {0}", [one.request]) : "",
        one.orders.length ? __("Ordered as {0}", [andList(one.orders)]) : "",
      ]
        .filter(Boolean)
        .join(" · "),
      value: money(one.grand_total, one.currency),
      under: one.valid_till ? (one.status === "Expired" ? __("Expired {0}", [date(one.valid_till)]) : __("Holds until {0}", [date(one.valid_till)])) : "",
      route: `/desk/supplier-quotation/${encodeURIComponent(one.name)}`,
      actions: [
        one.request && { label: __("Compare"), icon: "lucide-columns-3", onClick: () => compare(one.request) },
        said.value.can.order && ["Submitted", "Partially Ordered"].includes(one.status) && { label: __("Order"), icon: "lucide-shopping-cart", onClick: () => onedesk().quotes.order(one.name) },
      ].filter(Boolean),
    };
  })
);

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
  props.onTitle?.({ title: __("Quotes") });
  extended(s);
  props.onActions?.([s.can.ask && { label: __("Ask for Prices"), primary: true, onClick: () => onedesk().quotes.ask(load) }].filter(Boolean));
}

// The page is a place (one_studio/places.py): its extensions are told what
// it shows, and may add a note or a button.
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
