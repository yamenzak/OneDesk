<template>
  <!-- The customer's invoices for the project and those under it, newest
       first, each with what it's for, what's owed now and what's held, and
       Record Payment, Release Retention and Send on it
       (one_project/billing.py `invoices`). -->
  <div class="pb-12">
    <Loading v-if="!said" />
    <template v-else>
      <!-- The title and what can be done, on one line as on Time. -->
      <div class="flex flex-wrap items-center gap-2 pb-2">
        <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
          <span class="lucide-receipt size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Invoices") }}
          <span v-if="said.invoices.length" class="text-base font-normal text-ink-gray-5">{{ said.invoices.length }}</span>
        </h2>
        <span v-if="oneCurrency" class="text-sm text-ink-gray-5">{{ __("Amounts in {0}", [oneCurrency]) }}</span>
        <Button v-if="said.totals.retention && said.can_pay" size="sm" icon-left="lucide-hand-coins" :label="__('Release Retention')" @click="release()" />
        <Button v-if="said.can_create && kind === 'Retainer'" size="sm" variant="solid" icon-left="lucide-receipt" :label="__('Invoice Month')" @click="invoiceMonth" />
        <Button v-else-if="said.can_create" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Invoice')" @click="newInvoice" />
      </div>
      <Figures v-if="said.invoices.length || said.totals.advance" class="mb-5 mt-3" :figures="figures" />

      <div v-if="!said.invoices.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-receipt size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No invoices") }}</p>
      </div>
      <List v-else :columns="columns" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Invoice") }}</ListHeaderCell>
          <ListHeaderCell v-if="byParty" class="max-md:hidden">{{ __("Customer") }}</ListHeaderCell>
          <ListHeaderCell class="max-lg:hidden">{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Due") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Total") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Outstanding") }}</ListHeaderCell>
          <ListHeaderCell v-if="holds" class="justify-end max-md:hidden">{{ __("Retention") }}</ListHeaderCell>
          <ListHeaderCell />
        </ListHeader>
        <ListRows :items="said.invoices" row-key="name" v-slot="{ item }">
          <ListRow @click="go(`/desk/sales-invoice/${item.name}`)">
            <ListCell class="min-w-0">
              <div class="min-w-0">
                <div class="truncate text-base text-ink-gray-8">{{ forText(item) || item.name }}</div>
                <div class="truncate text-sm text-ink-gray-5">{{ [forText(item) ? item.name : "", item.where].filter(Boolean).join(" · ") }}</div>
              </div>
            </ListCell>
            <ListCell v-if="byParty" class="min-w-0 gap-2 max-md:hidden"><Avatar :label="item.party" :image="item.party_image" shape="square" size="sm" /><span class="truncate text-ink-gray-7">{{ item.party }}</span></ListCell>
            <ListCell class="tabular-nums text-ink-gray-7 max-lg:hidden">{{ date(item.date) }}</ListCell>
            <!-- When the part owed now is due; what's held says its own date. -->
            <ListCell class="tabular-nums max-md:hidden" :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ item.owed || item.status === "Draft" ? date(item.due) : "" }}</ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="STATUS[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8 max-md:hidden">{{ sum(item.total, item.currency) }}</ListCell>
            <ListCell class="justify-end tabular-nums" :class="item.owed ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ sum(item.status === "Draft" ? item.outstanding : item.owed, item.currency) }}</ListCell>
            <ListCell v-if="holds" class="justify-end max-md:hidden">
              <div v-if="item.held" class="min-w-0 text-end">
                <div class="tabular-nums text-ink-gray-8">{{ sum(item.held, item.currency) }}</div>
                <div class="truncate text-sm text-ink-gray-5">{{ __("Due {0}", [date(item.held_due)]) }}</div>
              </div>
            </ListCell>
            <ListCell class="justify-end" @click.stop>
              <Dropdown v-if="actions(item).length" :options="actions(item)" placement="right">
                <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
              </Dropdown>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, __, call, date, emailRecord, followList, go, money, monthName, newDoc, onedesk, plain } from "../kit";
import { onlyArg, useOnly } from "./only";

const props = defineProps({ projectName: { type: String, required: true }, projectTitle: String, kind: String, customer: String, currency: String });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();

// ERPNext's own colours for an invoice's status.
const STATUS = { Paid: "green", "Partly Paid": "blue", Unpaid: "orange", Overdue: "red", Draft: "red", Return: "gray", "Credit Note Issued": "gray" };
const said = ref(null);
// The figures are in the company's currency, said once at the top when the
// invoices are in it too.
const amount = (value) => (oneCurrency.value === props.currency ? plain(value) : money(value, props.currency));

async function load() {
  said.value = await call("onedesk.one_project.billing.invoices", { project: props.projectName, ...onlyArg(only) });
}
let timer = null;
const later = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
// A payment changes what's owed on an invoice, so both are followed.
const stops = [followList("Sales Invoice", later), followList("Payment Entry", later)];
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearTimeout(timer);
});
watch(() => props.projectName, load, { immediate: true });

const share = (part, whole) => (whole ? Math.max(0, Math.min(100, Math.round((100 * part) / whole))) : undefined);
const figures = computed(() => {
  const t = said.value.totals;
  return [
    { title: __("Invoiced"), value: amount(t.invoiced), note: t.drafts ? (t.drafts === 1 ? __("1 draft") : __("{0} drafts", [t.drafts])) : "" },
    { title: __("Paid"), value: amount(t.paid), bar: share(t.paid, t.invoiced), note: t.advance ? __("{0} paid in advance", [amount(t.advance)]) : "" },
    { title: __("Outstanding"), value: amount(t.outstanding) },
    { title: __("Overdue"), value: amount(t.overdue), alarm: t.overdue > 0, note: t.late ? (t.late === 1 ? __("1 invoice") : __("{0} invoices", [t.late])) : "" },
    ...(t.retention
      ? [
          { title: __("Retention Held"), value: amount(t.retention) },
        ]
      : []),
  ];
});

// One customer needs no column; amounts in one currency are said once, at
// the top, as on Money (frappe's own number format).
const byParty = computed(() => said.value.parties > 1);
const holds = computed(() => said.value.invoices.some((one) => one.held));
const oneCurrency = computed(() => {
  const found = new Set(said.value.invoices.map((one) => one.currency));
  return found.size === 1 ? [...found][0] : null;
});
const sum = (value, currency) => (oneCurrency.value ? plain(value) : money(value, currency));
const columns = computed(() => {
  const party = byParty.value;
  const held = holds.value;
  return {
    base: ["minmax(0,1fr)", "auto", "6.5rem", "2rem"],
    md: ["minmax(9rem,1.3fr)", party && "minmax(6rem,1fr)", "7rem", "7.5rem", "7rem", "7rem", held && "7rem", "2rem"].filter(Boolean),
    lg: ["minmax(12rem,1.3fr)", party && "minmax(8rem,1fr)", "6.5rem", "6.5rem", "7.5rem", "7.5rem", "7.5rem", held && "7.5rem", "2rem"].filter(Boolean),
  };
});

// What an invoice is for, as billing.for_what says it.
function forText(item) {
  const one = item.for || {};
  if (one.kind === "credit") return __("Credit note");
  if (one.kind === "progress") return __("Work done {0}%", [one.value]);
  if (one.kind === "month") return monthName(one.value);
  if (one.kind === "time") return __("{0} h of time", [one.value]);
  if (one.kind === "time_costs") return __("{0} h of time and costs", [one.value]);
  if (one.kind === "costs") return __("Costs");
  if (one.kind === "items") return one.more ? __("{0} +{1}", [one.value, one.more]) : one.value;
  return "";
}

// Record Payment is the invoice's own (OneBook's, one_book/heads.py); Send
// opens the invoice with frappe's Email on it, its print attached.
function actions(item) {
  const found = [];
  if (item.can_pay && said.value.can_pay) found.push({ label: __("Record Payment"), icon: "lucide-banknote", onClick: () => pay(item) });
  if (item.held && said.value.can_pay) found.push({ label: __("Release Retention"), icon: "lucide-hand-coins", onClick: () => release(item.name) });
  if (item.status !== "Draft") found.push({ label: __("Send"), icon: "lucide-send", onClick: () => send(item) });
  return found;
}
async function pay(item) {
  const verb = await call("onedesk.one.head.offer", { doctype: "Sales Invoice", name: item.name, verb: "invoice.record_payment" });
  if (verb) onedesk().head.act({ doctype: "Sales Invoice", doc: { name: item.name }, reload_doc: load }, verb);
}
const send = (item) => emailRecord("Sales Invoice", item.name);
// The customer's payment for the retention held, ERPNext's own Payment
// Entry matched to each invoice's retention terms (one_project/retention.py).
const release = (invoice) => onedesk().project.release_retention({ project: props.projectName, doctype: "Sales Invoice", invoice });

const newInvoice = () => newDoc("Sales Invoice", { customer: props.customer, project: props.projectName });
const invoiceMonth = () =>
  onedesk().project.invoice_month({ doctype: "Project", doc: { name: props.projectName, project_name: props.projectTitle, customer: props.customer } });
</script>
