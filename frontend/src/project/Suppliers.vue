<template>
  <!-- What the project buys. Subcontracts, the packages of work billed as
       they get done, are cards: what each is for, how far it's billed, what's
       held and what's to pay, with Bill Progress for the next bill
       (one_project/money.py `_suppliers`, progress.py). Then the suppliers'
       bills (billing.py `bills`), and Buying: requests, quotations, orders
       for goods and receipts (buying.py). -->
  <div class="pb-12">
    <div class="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2">
      <div v-if="orders.length" class="flex flex-wrap gap-x-6 gap-y-1 text-base text-ink-gray-6">
        <span>{{ __("Ordered") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("ordered")) }}</span></span>
        <span>{{ __("Billed") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("billed")) }}</span></span>
        <span>{{ __("Left to Bill") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("left")) }}</span></span>
        <span v-if="bills?.totals.outstanding">{{ __("To Pay") }} <span class="tabular-nums text-ink-gray-9">{{ amount(bills.totals.outstanding) }}</span></span>
        <span v-if="bills?.totals.overdue" class="text-ink-red-5">{{ __("Overdue") }} <span class="tabular-nums">{{ amount(bills.totals.overdue) }}</span></span>
        <span v-if="total('retention')">{{ __("Retention Held") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("retention")) }}</span></span>
      </div>
      <div class="ms-auto flex gap-2">
        <Button v-if="contacts?.can_change" size="sm" icon-left="lucide-plus" :label="__('Add Supplier')" @click="addSupplier" />
        <!-- A bill with no order before it, a shop receipt: the project filled in. -->
        <Button v-if="cash.can_bill" size="sm" icon-left="lucide-receipt" :label="__('Record Bill')" @click="newDoc('Purchase Invoice', { project: said.name })" />
        <Button v-if="cash.can_order" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Purchase Order')" @click="order" />
      </div>
    </div>

    <div v-if="waiting.length" class="mb-6">
      <h2 class="mb-2 text-base font-medium text-ink-gray-7">{{ __("No Order Yet") }}</h2>
      <div class="flex flex-wrap gap-2">
        <Button v-for="one in waiting" :key="one.row" size="sm" variant="subtle" :label="[one.company, __(one.role)].join(' · ')" @click="editSupplier(one)" />
      </div>
    </div>

    <div v-if="!packages.length" class="flex flex-col items-center gap-3 py-12 text-center">
      <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-truck size-5" /></span>
      <p class="text-base text-ink-gray-7">{{ __("No subcontracts") }}</p>
    </div>

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

        <!-- The supplier's contract for the project (agreement.py). -->
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

    <section v-if="bills?.bills.length" class="mt-8">
      <h2 class="mb-3 text-lg font-semibold text-ink-gray-9">{{ __("Bills") }}</h2>
      <List :columns="{ base: ['minmax(0,1fr)', 'auto', '6.5rem', '2rem'], md: ['minmax(9rem,1.3fr)', 'minmax(6rem,1fr)', '8rem', '8.5rem', '8rem', '8rem', '2rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Bill") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Supplier") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Due") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Total") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Outstanding") }}</ListHeaderCell>
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
            <ListCell class="min-w-0 gap-2 max-md:hidden"><Avatar :label="item.party" :image="item.party_image" shape="square" size="sm" /><span class="truncate text-ink-gray-7">{{ item.party }}</span></ListCell>
            <ListCell class="min-w-0 tabular-nums max-md:hidden">
              <div v-if="item.retention_due" class="min-w-0">
                <div class="text-ink-gray-7">{{ date(item.retention_due) }}</div>
                <div class="truncate text-sm text-ink-gray-5">{{ __("Retention") }}</div>
              </div>
              <span v-else :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ date(item.due) }}</span>
            </ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="BILL[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ money(item.total, item.currency) }}</ListCell>
            <ListCell class="justify-end tabular-nums max-md:hidden" :class="item.outstanding ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ money(item.outstanding, item.currency) }}</ListCell>
            <ListCell class="justify-end" @click.stop>
              <Dropdown v-if="billActions(item).length" :options="billActions(item)" placement="right">
                <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
              </Dropdown>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>

    <section class="mt-8">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Buying") }}</h2>
        <div class="ms-auto flex gap-2">
          <Button v-if="buying?.can_request" size="sm" icon-left="lucide-plus" :label="__('New Material Request')" @click="newDoc('Material Request', { project: said.name, material_request_type: 'Purchase' })" />
          <Button v-if="buying?.can_ask" size="sm" icon-left="lucide-plus" :label="__('Request Prices')" @click="newDoc('Request for Quotation', { project: said.name })" />
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
            <ListCell><Badge :label="__(item.status)" :theme="PAPER[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8 max-md:hidden">{{ item.amount ? money(item.amount, item.currency || cash.currency) : "" }}</ListCell>
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

import { Loading, __, call, date, followList, go, money, newDoc, onedesk } from "../kit";
import { onlyArg, useOnly } from "./only";

const props = defineProps({ said: { type: Object, required: true } });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();

const STATUS = { "On Hold": "orange", Closed: "gray", Completed: "green" };
const cash = computed(() => props.said.money);
const orders = computed(() => cash.value.suppliers);
// Goods are on Buying, with what's received; the cards are the packages of work.
const packages = computed(() => orders.value.filter((one) => one.subcontract));
// A supplier's contracts on the project, newest first.
const signedWith = (supplier) => (props.said.contracts || []).filter((one) => one.party_type === "Supplier" && one.party === supplier);
const amount = (value) => money(value, cash.value.currency);
const total = (key) => orders.value.reduce((sum, one) => sum + (one[key] || 0), 0);
const billedShare = (one) => (one.ordered ? Math.min(100, Math.round((100 * one.billed) / one.ordered)) : 0);
const late = (days) => (days === 1 ? __("1 day late") : __("{0} days late", [days]));

function facts(one) {
  const shown = [
    { label: __("Billed"), value: amount(one.billed) },
    { label: __("Left to Bill"), value: amount(one.left) },
    { label: __("Paid"), value: amount(one.paid) },
  ];
  if (one.to_pay) shown.push({ label: __("To Pay"), value: amount(one.to_pay), alarm: Boolean(one.late) });
  if (one.retention) shown.push({ label: __("Retention Held"), value: amount(one.retention) });
  if (one.advance) shown.push({ label: __("Advance"), value: amount(one.advance) });
  return shown;
}

// Bill Progress is desk's own dialog, the one on the order's form.
const bill = (one) => onedesk().progress.ask({ doctype: "Purchase Order", doc: { name: one.order } });
const order = () => newDoc("Purchase Order", { project: props.said.name });

// The suppliers' bills, as the Invoices view lists the customer's.
const BILL = { Paid: "green", "Partly Paid": "blue", Unpaid: "orange", Overdue: "red", Draft: "red", Return: "gray", "Debit Note Issued": "gray" };
const bills = ref(null);
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
// Record Payment, and Pay Retention for what's held from the bill, matched to
// its retention terms (one_project/retention.py `release`).
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

// Buying: ERPNext's statuses, coloured as its lists colour them.
const PAPER = {
  Draft: "red", Pending: "orange", "Partially Ordered": "orange", Ordered: "green", Received: "green", "Partially Received": "orange",
  Submitted: "blue", "To Pay": "orange", "To Bill": "orange", "To Receive": "orange", "To Receive and Bill": "orange", Completed: "green", Closed: "gray",
  Stopped: "red", Expired: "gray", Cancelled: "red",
};
const slug = (doctype) => doctype.toLowerCase().replaceAll(" ", "-");
// An order for goods says how much has come, and warns when it's billed ahead.
const received = (item) =>
  item.received === null || item.received === undefined ? "" : [__("{0}% received", [Math.round(item.received)]), __("{0}% billed", [Math.round(item.billed)])].join(" · ");
const ahead = (item) => item.billed > item.received;
const buying = ref(null);

// The suppliers on the project with nothing ordered from them yet: its
// Contacts as Subcontractor or Supplier (one_project/contacts.py).
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
    call("onedesk.one_project.buying.papers", { project: props.said.name, ...onlyArg(only) }),
    call("onedesk.one_project.billing.bills", { project: props.said.name, ...onlyArg(only) }),
    call("onedesk.one_project.contacts.contacts", { project: props.said.name }),
  ]);
}
watch(() => [props.said.name, props.said.modified, cash.value.open_orders, cash.value.spent], load, { immediate: true });
// A payment changes what's owed on a bill.
let timer = null;
const later = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
const stops = [followList("Purchase Invoice", later), followList("Payment Entry", later)];
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearTimeout(timer);
});
</script>
