<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <header class="pt-6">
        <div class="flex items-start justify-between gap-6">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <button v-if="said.brand" class="flex items-center gap-1.5 text-sm text-ink-gray-6 hover:text-ink-gray-8" @click="go(`/desk/item?brand=${encodeURIComponent(said.brand)}`)">
                <img v-if="said.brand_logo" :src="said.brand_logo" alt="" class="size-4 rounded-1 object-contain" />
                <span>{{ said.brand }}</span>
              </button>
              <span v-if="said.brand" class="text-ink-gray-4" aria-hidden="true">·</span>
              <Badge :label="__(KIND[said.kind] || said.kind)" theme="gray" size="md" />
              <Badge v-if="said.made" :label="__('Made Here')" theme="blue" size="md" />
              <Badge v-if="said.disabled" :label="__('Disabled')" theme="red" size="md" />
              <button v-if="said.variant_of" class="text-sm text-ink-gray-5 hover:text-ink-gray-8" @click="go(`/desk/item/${encodeURIComponent(said.variant_of)}`)">
                {{ __("Variant of {0}", [said.variant_of_title || said.variant_of]) }}
              </button>
            </div>
            <div class="mt-3 flex items-center gap-4">
              <button
                class="shrink-0 rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                :class="said.can_write ? 'cursor-pointer' : 'cursor-default'"
                :aria-label="said.image ? __('Change Picture') : __('Add Picture')"
                @click="picture"
              >
                <Avatar :image="said.image" :label="said.item_name" shape="square" size="3xl" class="size-14" />
              </button>
              <Title class="min-w-0" :said="{ title: said.item_name, can_write: said.can_write }" size="text-3xl lg:text-4xl" field="item_name" :label="__('Item Name')" @change="set" />
            </div>
            <p v-if="headline" class="mt-1 text-base" :class="TONE[said.headline.tone]">{{ headline }}</p>
            <dl class="mt-4 flex flex-wrap gap-x-8 gap-y-3 text-base">
              <div v-for="one in facts" :key="one.label" class="flex min-w-0 flex-col gap-1">
                <dt class="text-sm text-ink-gray-5">{{ one.label }}</dt>
                <dd class="truncate py-1 text-ink-gray-8">
                  <FieldEdit v-if="one.field" :form="form" :field="one.field" :label="one.label" :placeholder="one.placeholder" @saved="load" />
                  <button v-else-if="one.route" :class="LINK" @click="go(one.route)">{{ one.value }}</button>
                  <span v-else>{{ one.value }}</span>
                </dd>
              </div>
            </dl>
          </div>
          <ItemBarcodes v-if="wide" :item="said.name" :barcodes="said.barcodes" :can-write="said.can_write" class="shrink-0" @changed="load" />
        </div>
        <ItemBarcodes v-if="!wide" :item="said.name" :barcodes="said.barcodes" :can-write="said.can_write" class="mt-4 !items-start" @changed="load" />
        <Figures v-if="figures.length" :figures="figures" :columns="figures.length" class="mt-5" />
      </header>

      <PlaceSpot :said="placed" class="mt-4" />
      <WindowPart v-if="onWindow" :win="win" part="row"><ViewTabs v-model="view" :views="VIEWS" row /></WindowPart>
      <ViewTabs v-else v-model="view" :views="VIEWS" class="mt-5" />

      <div class="pt-4">
        <ItemOverview v-if="view === 'overview'" :said="said" :form="form" @changed="load" @view="(key) => (view = key)" @several="several = true" />
        <ItemStock v-else-if="view === 'stock'" :said="said" :form="form" @changed="load" />
        <ItemBuying v-else-if="view === 'buying'" :said="said" :form="form" @changed="load" />
        <ItemSelling v-else-if="view === 'selling'" :said="said" :form="form" @changed="load" />
        <ItemMaking v-else-if="view === 'making'" :said="said" :form="form" @changed="load" />
        <ItemFiles v-else-if="view === 'files'" :item="said.name" :title="said.item_name" @count="(n) => (fileCount = n)" />
        <div v-else-if="view === 'activity'" class="pb-12">
          <PlaceSpot :said="activitySpot" class="mb-3" />
          <Activity :key="said.name" doctype="Item" :name="said.name" />
        </div>
      </div>
      <WindowPart v-if="onWindow" :win="win" part="activity"><Activity :key="said.name" doctype="Item" :name="said.name" /></WindowPart>
      <ItemVariantsMake v-if="said.choices" v-model:open="several" :item="said.name" :choices="said.choices" @made="load" />
    </template>
  </Page>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge } from "frappe-ui";

import { FieldEdit, Figures, Loading, Page, PlaceSpot, ViewTabs, WindowPart, __, call, date, follow, followList, go, money, onResize, onedesk, quantity, setQuery, setValue, upload, useForm, useRecord, viewWidth, windowRecord } from "../../kit";
import Title from "../../project/Title.vue";
import { usePlace } from "../../project/place";
import ItemBarcodes from "./ItemBarcodes.vue";
import ItemBuying from "./ItemBuying.vue";
import ItemFiles from "./ItemFiles.vue";
import ItemMaking from "./ItemMaking.vue";
import ItemOverview from "./ItemOverview.vue";
import ItemSelling from "./ItemSelling.vue";
import ItemStock from "./ItemStock.vue";
import ItemVariantsMake from "./ItemVariantsMake.vue";

const Activity = defineAsyncComponent(() => import("../../project/Activity.vue"));

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onStatus: Function,
  onActions: Function,
  win: { type: Object, default: null },
});

const onWindow = windowRecord(props.win);

const TONE = { red: "text-ink-red-5", orange: "text-ink-amber-6", gray: "text-ink-gray-5" };
const LINK = "text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-4 hover:decoration-ink-gray-8";
const KIND = { Stock: "Stock Item", Service: "Service", "Fixed Asset": "Equipment", Template: "Template" };

const name = computed(() => props.route[0]);
const wide = ref(viewWidth() >= 640);
onBeforeUnmount(onResize(() => (wide.value = viewWidth() >= 640)));
const said = ref(null);
const view = ref(props.query.view || "overview");
const fileCount = ref(null);
const several = ref(false);
const record = useRecord("Item", name);
const form = useForm("Item", name);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_inventory.view.read", { item: asked });
  if (asked !== name.value) return;
  said.value = got;
  if (fileCount.value === null) fileCount.value = got.files;
  report();
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
async function files() {
  const asked = name.value;
  const got = await call("onedesk.one_inventory.view.files", { item: asked });
  if (asked === name.value) fileCount.value = got;
}
let stop = [];
watch(
  name,
  (now) => {
    stop.forEach((one) => one());
    said.value = null;
    fileCount.value = null;
    if (!now) return;
    stop = [
      follow("Item", now, load),
      followList("Item", (data) => said.value?.has_variants && data.name !== now && soon()),
      followList("Item Attribute", () => said.value?.has_variants && soon()),
      followList("File", files),
      ...[
        "Bin",
        "Stock Ledger Entry",
        "Stock Entry",
        "Serial No",
        "Purchase Order",
        "Supplier Quotation",
        "Blanket Order",
        "Item Manufacturer",
        "Quotation",
        "Sales Order",
        "Sales Invoice",
        "Work Order",
        "Material Request",
        "Item Price",
        "BOM",
        "Asset",
        "Employee",
      ].map((one) => followList(one, soon)),
    ];
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(view, (now) => setQuery("view", now === "overview" ? null : now));
watch(() => props.query.view, (now) => now && (view.value = now));
watch(() => said.value?.modified, (now, before) => {
  if (now && before && now !== before) record.reload();
  form.reload(now);
});
watch(record.record, () => said.value && report());

const VIEWS = computed(() => {
  const s = said.value;
  if (!s) return [];
  const open = (list) => list?.filter((one) => one.left).length || null;
  return [
    { key: "overview", label: __("Overview"), icon: "lucide-layout-dashboard" },
    s.stock && { key: "stock", label: __("Stock"), icon: "lucide-warehouse", count: s.stock.places.length || null },
    s.buying && { key: "buying", label: __("Buying"), icon: "lucide-shopping-cart", count: open(s.buying.orders) },
    s.selling && { key: "selling", label: __("Selling"), icon: "lucide-hand-coins", count: open(s.selling.orders) },
    s.making && { key: "making", label: __("Manufacturing"), icon: "lucide-hammer", count: s.making.orders.length || null },
    !onWindow && { key: "files", label: __("Files"), icon: "lucide-paperclip", count: fileCount.value || null },
    !onWindow && { key: "activity", label: __("Activity"), icon: "lucide-activity" },
  ].filter(Boolean);
});
watch(VIEWS, (now) => now.length && !now.some((one) => one.key === view.value) && (view.value = "overview"));

const uom = computed(() => said.value?.stock_uom);
const making = computed(() => (said.value?.making?.orders || []).reduce((sum, one) => sum + Math.max(one.qty - one.produced_qty, 0), 0));

const headline = computed(() => {
  const line = said.value?.headline;
  if (!line) return "";
  if (line.key === "disabled") return __("Disabled, so no new document can use it");
  if (line.key === "ended") return __("At the end of its life since {0}", [date(line.date)]);
  if (line.key === "short") {
    const short = __("{0} more promised than on hand", [quantity(line.qty, uom.value)]);
    return making.value ? __("{0}, {1} being made", [short, quantity(making.value)]) : short;
  }
  return __("Low in {0}", [line.names.join(", ")]);
});

const facts = computed(() => {
  const s = said.value;
  return [
    s.item_code !== s.item_name && { label: __("Item Code"), value: s.item_code },
    { label: __("Item Group"), field: "item_group" },
    { label: __("Default Unit of Measure"), field: "stock_uom" },
    { label: __("Brand"), field: "brand", placeholder: __("No brand") },
    s.stock && { label: __("Valuation Method"), field: "valuation_method", placeholder: __(s.valuation) },
    ...s.attributes.map((one) => ({ label: __(one.attribute), value: one.value })),
  ].filter(Boolean);
});

const traced = (data, type = "area") => (data?.some((value) => value) ? { data, type } : undefined);
function since(data) {
  const sparkline = traced(data);
  if (!sparkline) return {};
  const delta = data[data.length - 1] - data[data.length - 2];
  return { sparkline, delta: Math.abs(delta) > 1e-9 ? delta : null };
}

const figures = computed(() => {
  const s = said.value;
  const sum = s.summary || {};
  const trend = s.trends || {};
  const list = [];
  if (s.stock) {
    const places = s.stock.places.filter((one) => one.on_hand).length;
    const where = places > 1 ? __("In {0} warehouses", [places]) : places === 1 ? __("In {0}", [s.stock.places.find((one) => one.on_hand).warehouse]) : "";
    const held = since(trend.held);
    const worth = since(trend.worth);
    list.push(
      { title: __("On Hand"), value: quantity(sum.on_hand, uom.value), ...held, deltaFormat: (v) => quantity(v, uom.value), note: held.delta ? __("this month") : where, route: `/desk/query-report/Stock Balance?item_code=${encodeURIComponent(s.name)}` },
      { title: __("Free to Sell"), value: quantity(sum.free, uom.value), note: sum.on_hand - sum.free > 0 ? (sum.held ? __("{0} promised to customers, {1} of it held", [quantity(sum.on_hand - sum.free), quantity(sum.held)]) : __("{0} promised to customers", [quantity(sum.on_hand - sum.free)])) : "", alarm: sum.free < 0, bar: sum.on_hand > 0 ? Math.max(0, Math.min(100, (100 * sum.free) / sum.on_hand)) : null },
      { title: __("On Order"), value: quantity(sum.ordered, uom.value), note: making.value ? __("{0} being made", [quantity(making.value)]) : "", sparkline: traced(trend.ordered, "bar") },
      { title: __("Stock Value"), value: money(sum.value, s.currency), ...worth, deltaFormat: (v) => money(v, s.currency), note: worth.delta ? __("this month") : __("Valued by {0}", [__(s.valuation)]) },
    );
  }
  if (s.assets) {
    const drafts = s.assets.filter((one) => one.docstatus === 0).length;
    list.push({ title: __("Assets"), value: String(s.assets.length), note: drafts ? __("{0} not yet registered", [drafts]) : "", route: `/desk/asset?item_code=${encodeURIComponent(s.name)}` });
  }
  if (s.last_made) list.push({ title: __("Last Manufactured"), value: quantity(s.last_made.qty, uom.value), note: date(s.last_made.posting_date) });
  else if (s.last_bought) list.push({ title: s.last_bought.kind === "received" ? __("Last Received") : __("Last Ordered"), value: money(s.last_bought.rate, s.currency), note: __("{0}, from {1}", [date(s.last_bought.on_date), s.last_bought.supplier]), sparkline: trend.prices?.length > 1 ? traced(trend.prices, "line") : undefined });
  const price = s.selling?.prices?.find((one) => !one.customer);
  if (!s.stock && price) list.push({ title: __("Selling Price"), value: money(price.price_list_rate, price.currency), note: price.price_list });
  if (!s.stock && s.selling?.customers?.length) {
    list.push({ title: __("Sold in 12 Months"), value: money(s.selling.customers.reduce((all, one) => all + one.amount, 0), s.currency), note: __("To {0} customers", [s.selling.customers.length]) });
  }
  return list;
});

async function set(fieldname, value) {
  said.value[fieldname] = value;
  try {
    await setValue("Item", name.value, fieldname, value);
  } finally {
    load();
  }
}

function picture() {
  if (!said.value?.can_write) return;
  upload("Item", name.value, (file) => set("image", file.file_url), {
    allow_multiple: false,
    restrictions: { allowed_file_types: ["image/*"] },
  });
}

const desk = onedesk;
const details = () => desk().item.edit(name.value, said.value.modified, load);

function report() {
  const s = said.value;
  props.onTitle?.({
    title: s.item_name,
    between: [{ label: s.item_group, route: `/desk/item?item_group=${encodeURIComponent(s.item_group)}` }],
  });
  props.onStatus?.(null);
  extended(s);
  props.onActions?.([...actions(s), ...verbs, ...record.menu({ gone: () => go("/desk/item") })]);
}

function actions(s) {
  const list = [];
  const can = s.can;
  const usable = !s.disabled && !s.has_variants;
  if (usable && s.made && can["Work Order"]) list.push({ label: __("Make More"), primary: true, onClick: () => desk().item.make(s.name, s.made.name) });
  else if (usable && s.is_purchase_item && can["Purchase Order"]) list.push({ label: __("Order More"), primary: true, onClick: () => desk().item.order(s.name) });
  if (usable && s.is_purchase_item && can["Material Request"]) list.push({ label: __("Request Material"), onClick: () => desk().item.request(s.name) });
  if (usable && s.stock && can["Stock Entry"]) list.push({ label: __("Transfer Stock"), onClick: () => desk().item.move(s.name) });
  if (usable && s.stock && can["Stock Reconciliation"]) list.push({ label: s.stock.moves.length ? __("Count Stock") : __("Set Opening Stock"), onClick: () => desk().item.count(s.name, !s.stock.moves.length) });
  if (s.has_variants && can.Item) list.push({ label: __("Add Variant"), primary: true, onClick: () => desk().item.variant(s.name) });
  if (s.choices && can.Item) list.push({ label: __("Make Several Variants"), onClick: () => (several.value = true) });
  if (s.can_write) list.push({ label: __("Edit Details"), onClick: details });
  if (s.can_write) list.push({ label: s.disabled ? __("Enable Item") : __("Disable Item"), onClick: () => set("disabled", s.disabled ? 0 : 1) });
  if (s.stock) {
    for (const [label, report] of [[__("Stock Balance"), "Stock Balance"], [__("Stock Ledger"), "Stock Ledger"], [__("Stock Projected Qty"), "Stock Projected Qty"]]) {
      list.push({ label, onClick: () => go(`/desk/query-report/${report}?item_code=${encodeURIComponent(s.name)}`) });
    }
  }
  if (s.has_variants) list.push({ label: __("Variant Details Report"), onClick: () => go(`/desk/query-report/Item Variant Details?item=${encodeURIComponent(s.name)}`) });
  return list;
}

const activitySpot = usePlace("oneinventory_item.activity", () => (view.value === "activity" && said.value ? { item: { name: said.value.name, item_name: said.value.item_name } } : null));

const placed = reactive({ notes: [], actions: [] });
let verbs = [];
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  const doc = record.record.value?.doc;
  if (!places || !doc) return;
  const key = `${s.name}/${doc.modified}/${s.modified}/${JSON.stringify(s.summary)}`;
  if (drawn === key) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  verbs = [];
  const lend = () => ({
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
  if (places.listening("oneinventory_item.item")) {
    const sum = s.summary || {};
    const item = {
      name: s.name,
      item_name: s.item_name,
      item_group: s.item_group,
      kind: s.kind,
      uom: s.stock_uom,
      disabled: Boolean(s.disabled),
      on_hand: sum.on_hand ?? null,
      free: sum.free ?? null,
      on_order: sum.ordered ?? null,
      worth: sum.value ?? null,
      low_in: sum.below || [],
      made: Boolean(s.made),
    };
    places.emit("oneinventory_item.item", { item }, lend());
  }
  if (places.listening("record_head.drawn")) {
    const page = lend();
    const told = [];
    places.emit(
      "record_head.drawn",
      Object.fromEntries(Object.entries(doc).filter(([field]) => !field.startsWith("__"))),
      {
        verb: (label, handler) => told.push({ label: String(label || ""), onClick: () => handler(), button: true }),
        figure: (label, value) => page.note(`${label} · ${value ?? ""}`, "gray"),
        note: page.note,
      },
      "Item"
    );
    verbs = told;
  }
}
</script>
