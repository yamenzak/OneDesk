<template>
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-2">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-truck size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Suppliers") }}
        <span v-if="suppliers" class="text-base font-normal text-ink-gray-5">{{ suppliers }}</span>
      </h2>
      <Button v-if="contacts?.can_change" size="sm" icon-left="lucide-plus" :label="__('Add Supplier')" @click="addSupplier" />
      <Button v-if="cash.can_bill" size="sm" icon-left="lucide-receipt" :label="__('Record Bill')" @click="newDocIn('Purchase Invoice', { project: said.name }, parts)" />
      <Button v-if="cash.can_order" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Purchase Order')" @click="order" />
    </div>
    <PlaceSpot :said="spot" class="mt-3" />
    <Figures v-if="orders.length || bills?.bills.length" class="mb-2 mt-3" :figures="figures" />

    <div v-if="waiting.length" class="mb-6">
      <h2 class="mb-2 text-base font-medium text-ink-gray-7">{{ __("No Order Yet") }}</h2>
      <div class="flex flex-wrap gap-2">
        <Button v-for="one in waiting" :key="one.row" size="sm" variant="subtle" :label="[one.company, __(one.role)].join(' · ')" @click="editSupplier(one)" />
      </div>
    </div>

    <section class="border-b border-outline-gray-1 py-5">
      <h2 class="mb-3 flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-hard-hat size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Subcontracts") }}
        <span v-if="packages.length" class="text-base font-normal text-ink-gray-5">{{ packages.length }}</span>
      </h2>
    <div v-if="!packages.length" class="py-3 text-base text-ink-gray-5">{{ __("No subcontracts") }}</div>

    <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="one in packages" :key="one.order" class="flex flex-col rounded-5 border border-outline-gray-2 bg-surface-base p-4">
        <div class="flex items-start gap-3">
          <Avatar :label="one.supplier" :image="one.image" shape="square" size="xl" />
          <div class="min-w-0 flex-1">
            <h3 class="truncate text-base font-semibold text-ink-gray-9">{{ one.supplier }}</h3>
            <p class="truncate text-sm text-ink-gray-7">{{ [one.for, one.where].filter(Boolean).join(" · ") }}</p>
            <button class="truncate text-sm text-ink-gray-5 hover:underline" @click="go(one.route)">{{ one.order }}<span v-if="one.ordered_on"> · {{ date(one.ordered_on) }}</span></button>
          </div>
          <Badge v-if="STATUS[one.status]" :label="__(one.status)" :theme="STATUS[one.status]" size="md" />
        </div>

        <button v-for="signed in signedWith(one.supplier_id)" :key="signed.name" class="mt-3 flex items-center gap-2 text-start text-sm text-ink-gray-7 enabled:hover:underline" :disabled="!signed.route" @click="go(signed.route)">
          <span class="h-2 w-2 shrink-0 rounded-full" :class="signed.signed ? 'bg-surface-green-5' : 'bg-surface-amber-5'" />
          {{ signed.signed ? (signed.ends ? __("Contract signed, ends {0}", [date(signed.ends)]) : __("Contract signed")) : __("Contract not signed yet") }}
        </button>

        <div class="mt-4 flex items-baseline justify-between gap-2">
          <span class="text-xl font-semibold tabular-nums text-ink-gray-9">{{ amount(one.ordered) }}</span>
          <span class="text-sm text-ink-gray-5">{{ billedShare(one) >= 100 ? __("Billed") : __("{0}% billed", [billedShare(one)]) }}</span>
        </div>
        <Progress :value="billedShare(one)" size="md" class="mt-2" />

        <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          <template v-for="fact in facts(one)" :key="fact.label">
            <dt class="text-ink-gray-5">{{ fact.label }}</dt>
            <dd class="text-end tabular-nums" :class="fact.alarm ? 'text-ink-red-5' : 'text-ink-gray-8'">{{ fact.value }}</dd>
          </template>
        </dl>
        <p v-if="one.to_pay && (one.late || one.due)" class="mt-1 text-end text-sm" :class="one.late ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ one.late ? late(one.late) : __("Due {0}", [date(one.due)]) }}</p>

        <div class="mt-auto flex items-center justify-end gap-2 pt-4">
          <Dropdown v-if="cash.can_pay && one.can_bill" :options="[{ label: __('Pay Advance'), icon: 'lucide-banknote', onClick: () => onedesk().project.pay_advance(one.order) }]" placement="right">
            <template #trigger><Button size="sm" variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
          <Button size="sm" variant="ghost" :label="__('Open Order')" @click="go(one.route)" />
          <Button v-if="cash.can_bill && one.can_bill" size="sm" :label="__('Bill Progress')" @click="bill(one)" />
        </div>
      </article>
    </div>
    </section>

    <section v-if="bills?.bills.length" class="border-b border-outline-gray-1 py-5">
      <h2 class="mb-3 flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-receipt size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Bills") }}
        <span v-if="bills.bills.length" class="text-base font-normal text-ink-gray-5">{{ bills.bills.length }}</span>
      </h2>
      <List :columns="billColumns" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Bill") }}</ListHeaderCell>
          <ListHeaderCell v-if="byParty" class="max-md:hidden">{{ __("Supplier") }}</ListHeaderCell>
          <ListHeaderCell class="max-lg:hidden">{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Due") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Total") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Outstanding") }}</ListHeaderCell>
          <ListHeaderCell />
        </ListHeader>
        <ListRows :items="bills.bills" row-key="name" v-slot="{ item }">
          <ListRow @click="go(`/desk/purchase-invoice/${item.name}`)">
            <ListCell class="min-w-0">
              <div class="min-w-0">
                <div class="truncate text-base text-ink-gray-8">{{ forText(item) || item.name }}</div>
                <div class="truncate text-sm text-ink-gray-5">{{ [forText(item) ? item.name : "", item.where].filter(Boolean).join(" · ") }}</div>
              </div>
            </ListCell>
            <ListCell v-if="byParty" class="min-w-0 gap-2 max-md:hidden"><Avatar :label="item.party" :image="item.party_image" shape="square" size="sm" /><span class="truncate text-ink-gray-7">{{ item.party }}</span></ListCell>
            <ListCell class="tabular-nums text-ink-gray-7 max-lg:hidden">{{ date(item.date) }}</ListCell>
            <ListCell class="tabular-nums max-md:hidden" :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ item.owed || item.status === "Draft" ? date(item.due) : "" }}</ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="BILL[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8 max-md:hidden">{{ sum(item.total, item.currency) }}</ListCell>
            <ListCell class="justify-end">
              <div class="min-w-0 text-end">
                <div class="tabular-nums" :class="item.outstanding ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ sum(item.outstanding, item.currency) }}</div>
                <div v-if="item.held" class="truncate text-sm text-ink-gray-5" :title="__('Due {0}', [date(item.held_due)])">{{ __("{0} held", [sum(item.held, item.currency)]) }}</div>
              </div>
            </ListCell>
            <ListCell class="justify-end" @click.stop>
              <Dropdown v-if="billActions(item).length" :options="billActions(item)" placement="right">
                <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
              </Dropdown>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>

    <section class="py-5">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
          <span class="lucide-shopping-cart size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Buying") }}
          <span v-if="buying?.papers.length" class="text-base font-normal text-ink-gray-5">{{ buying.papers.length }}</span>
        </h2>
        <div class="ms-auto flex gap-2">
          <Button v-if="buying?.can_request" size="sm" icon-left="lucide-plus" :label="__('New Material Request')" @click="newDocIn('Material Request', { project: said.name, material_request_type: 'Purchase' }, parts)" />
          <Button v-if="buying?.can_ask" size="sm" icon-left="lucide-plus" :label="__('Ask for Prices')" @click="askPrices" />
        </div>
      </div>
      <Loading v-if="!buying" />
      <div v-else-if="!buying.papers.length" class="py-3 text-base text-ink-gray-5">{{ __("Nothing requested or received") }}</div>
      <List v-else :columns="{ base: ['minmax(0,1fr)', 'auto'], md: ['minmax(10rem,1.2fr)', 'minmax(8rem,1fr)', '7rem', '8rem', '8rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Document") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Supplier") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Amount") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="buying.papers" row-key="name" v-slot="{ item }">
          <ListRow @click="go(`/desk/${slug(item.doctype)}/${encodeURIComponent(item.name)}`)">
            <ListCell class="min-w-0">
              <div class="min-w-0">
                <div class="truncate text-base text-ink-gray-8">{{ __(item.doctype) }}<span v-if="item.what" class="text-ink-gray-5"> · {{ item.what }}</span></div>
                <div class="truncate text-sm" :class="ahead(item) ? 'text-ink-amber-3' : 'text-ink-gray-5'">{{ [item.name, received(item)].filter(Boolean).join(" · ") }}</div>
              </div>
            </ListCell>
            <ListCell class="min-w-0 gap-2 max-md:hidden"><Avatar v-if="item.party_image" :label="item.party" :image="item.party_image" shape="square" size="sm" /><span class="truncate text-ink-gray-7">{{ item.party || "–" }}</span></ListCell>
            <ListCell class="tabular-nums text-ink-gray-7 max-md:hidden">{{ item.date ? date(item.date) : "" }}</ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="item.tone ? TONE[item.tone] : PAPER[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8 max-md:hidden">{{ item.amount ? sum(item.amount, item.currency || cash.currency) : "" }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, PlaceSpot, __, call, date, followList, go, money, newDocIn, onedesk, requires } from "../kit";
import { useParts } from "./parts";
import { usePlace } from "./place";

const props = defineProps({ said: { type: Object, required: true } });
const parts = useParts();

const STATUS = { "On Hold": "amber", Closed: "gray", Completed: "green" };
const cash = computed(() => props.said.money);
const orders = computed(() => cash.value.suppliers);
const packages = computed(() => orders.value.filter((one) => one.subcontract));
const signedWith = (supplier) => (props.said.contracts || []).filter((one) => one.party_type === "Supplier" && one.party === supplier);
const amount = (value) => money(value, cash.value.currency);
const sum = (value, currency) => money(value, currency || cash.value.currency);
const suppliers = computed(() => new Set(orders.value.map((one) => one.supplier_id)).size);
const share = (part, whole) => (whole ? Math.max(0, Math.min(100, Math.round((100 * part) / whole))) : undefined);
const figures = computed(() => {
  const t = bills.value?.totals || {};
  const ordered = total("ordered");
  return [
    { title: __("Ordered"), value: amount(ordered), note: total("left") ? __("{0} left to bill", [amount(total("left"))]) : "" },
    { title: __("Billed"), value: amount(t.invoiced || total("billed")), other: t.invoiced && Math.abs(t.invoiced - t.invoiced_net) >= 0.005 ? { label: __("Before tax"), value: amount(t.invoiced_net) } : undefined, bar: share(t.invoiced || total("billed"), ordered) },
    { title: __("Paid"), value: amount(t.paid), note: t.advance ? __("{0} paid in advance", [amount(t.advance)]) : "" },
    { title: __("To Pay"), value: amount(t.owed_now), alarm: t.overdue > 0, note: t.overdue ? __("{0} overdue", [amount(t.overdue)]) : "" },
    ...(t.retention ? [{ title: __("Retention Held"), value: amount(t.retention) }] : []),
  ];
});
const total = (key) => orders.value.reduce((sum, one) => sum + (one[key] || 0), 0);
const spot = usePlace("oneproject.suppliers", () => ({
  project: { name: props.said.name, title: props.said.title, kind: props.said.kind, currency: cash.value.currency },
  suppliers: {
    count: suppliers.value,
    subcontracts: packages.value.length,
    ordered: total("ordered"),
    to_pay: total("to_pay"),
    overdue: total("overdue"),
    retention: total("retention"),
  },
}));
const billedShare = (one) => (one.ordered ? Math.min(100, Math.round((100 * one.billed) / one.ordered)) : 0);
const late = (days) => (days === 1 ? __("1 day late") : __("{0} days late", [days]));

function facts(one) {
  const shown = [
    { label: __("Billed"), value: amount(one.billed) },
    { label: __("Left to Bill"), value: amount(one.left) },
    { label: __("Paid"), value: amount(one.paid) },
  ];
  if (one.to_pay) shown.push({ label: __("To Pay"), value: amount(one.to_pay), alarm: Boolean(one.late) });
  if (one.rate) shown.push({ label: __("Retention"), value: one.retention ? __("{0}% · {1} held", [one.rate, amount(one.retention)]) : `${one.rate}%` });
  if (one.advance) shown.push({ label: __("Advance"), value: amount(one.advance) });
  return shown;
}

const bill = (one) => onedesk().progress.ask({ doctype: "Purchase Order", doc: { name: one.order } });
const order = () => newDocIn("Purchase Order", { project: props.said.name }, parts.value);

const BILL = { Paid: "green", "Partly Paid": "blue", Unpaid: "amber", Overdue: "red", Draft: "red", Return: "gray", "Debit Note Issued": "gray" };
const bills = ref(null);
const byParty = computed(() => (bills.value?.parties || 0) > 1);
const billColumns = computed(() => ({
  base: ["minmax(0,1fr)", "auto", "6.5rem", "2rem"],
  md: ["minmax(9rem,1.3fr)", byParty.value && "minmax(6rem,1fr)", "7.5rem", "7rem", "7rem", "7rem", "2rem"].filter(Boolean),
  lg: ["minmax(12rem,1.3fr)", byParty.value && "minmax(8rem,1fr)", "6.5rem", "6.5rem", "7.5rem", "7.5rem", "7.5rem", "2rem"].filter(Boolean),
}));
function forText(item) {
  const one = item.for || {};
  if (one.kind === "credit") return __("Debit note");
  if (one.kind === "progress") return __("Work done {0}%", [one.value]);
  if (one.kind === "items") return one.more ? __("{0} +{1}", [one.value, one.more]) : one.value;
  return "";
}
async function pay(item) {
  const verb = await call("onedesk.one.head.offer", { doctype: "Purchase Invoice", name: item.name, verb: "invoice.record_payment" });
  if (verb) onedesk().head.act({ doctype: "Purchase Invoice", doc: { name: item.name }, reload_doc: load }, verb);
}
function billActions(item) {
  if (!bills.value.can_pay) return [];
  return [
    item.can_pay && { label: __("Record Payment"), icon: "lucide-banknote", onClick: () => pay(item) },
    item.held && {
      label: __("Pay Retention"),
      icon: "lucide-hand-coins",
      onClick: () => onedesk().project.release_retention({ project: props.said.name, doctype: "Purchase Invoice", invoice: item.name }),
    },
  ].filter(Boolean);
}

const TONE = { red: "red", orange: "amber", blue: "blue", green: "green", gray: "gray" };
const PAPER = {
  Draft: "red", Pending: "amber", "Partially Ordered": "amber", Ordered: "green", Received: "green", "Partially Received": "amber",
  Submitted: "blue", "To Pay": "amber", "To Bill": "amber", "To Receive": "amber", "To Receive and Bill": "amber", Completed: "green", Closed: "gray",
  Stopped: "red", Expired: "gray", Cancelled: "red",
};
const slug = (doctype) => doctype.toLowerCase().replaceAll(" ", "-");
const askPrices = () =>
  requires(["/assets/onedesk/js/one_inventory/quotes_actions.js"]).then(() => onedesk().quotes.ask(load, { project: props.said.name }));
const received = (item) =>
  item.received === null || item.received === undefined ? "" : [__("{0}% received", [Math.round(item.received)]), __("{0}% billed", [Math.round(item.billed)])].join(" · ");
const ahead = (item) => item.billed > item.received;
const buying = ref(null);

const contacts = ref(null);
const waiting = computed(() =>
  (contacts.value?.contacts || []).filter(
    (one) => ["Subcontractor", "Supplier"].includes(one.role) && one.supplier && !orders.value.some((order) => order.supplier_id === one.supplier)
  )
);
const addSupplier = () =>
  onedesk().project.contact(props.said.name, null, (now) => (contacts.value = now), { role: "Subcontractor", title: __("Add Supplier") });
const editSupplier = (one) => onedesk().project.contact(props.said.name, one, (now) => (contacts.value = now));

async function load() {
  [buying.value, bills.value, contacts.value] = await Promise.all([
    call("onedesk.one_project.buying.papers", { project: props.said.name }),
    call("onedesk.one_project.billing.bills", { project: props.said.name }),
    call("onedesk.one_project.contacts.contacts", { project: props.said.name }),
  ]);
}
watch(() => [props.said.name, props.said.modified, cash.value.open_orders, cash.value.spent], load, { immediate: true });
let timer = null;
const later = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
const stops = ["Purchase Invoice", "Payment Entry", "Supplier", "Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Order", "Purchase Receipt"].map((doctype) =>
  followList(doctype, later)
);
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearTimeout(timer);
});
</script>
