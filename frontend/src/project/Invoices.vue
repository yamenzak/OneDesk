<template>
  <!-- The customer's invoices for the project and those under it, newest
       first, each with what it's for, and Record Payment and Send on it
       (one_project/billing.py `invoices`). -->
  <div class="pb-12 pt-2">
    <Loading v-if="!said" />
    <template v-else>
      <Section v-if="said.invoices.length || said.totals.advance" :title="__('Invoices')">
        <Figures :figures="figures" />
      </Section>

      <div class="mb-3 mt-5 flex items-center gap-2">
        <Button v-if="said.can_create && kind === 'Retainer'" class="ms-auto" size="sm" variant="solid" icon-left="lucide-receipt" :label="__('Invoice Month')" @click="invoiceMonth" />
        <Button v-else-if="said.can_create" class="ms-auto" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Invoice')" @click="newInvoice" />
      </div>

      <div v-if="!said.invoices.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-receipt size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No invoices") }}</p>
      </div>
      <List v-else :columns="{ base: ['minmax(0,1fr)', 'auto', '6.5rem', '2rem'], md: ['minmax(12rem,1fr)', '7rem', '8rem', '8.5rem', '8rem', '8rem', '2rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Invoice") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Due") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Total") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Outstanding") }}</ListHeaderCell>
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
            <ListCell class="tabular-nums text-ink-gray-7 max-md:hidden">{{ date(item.date) }}</ListCell>
            <ListCell class="min-w-0 tabular-nums max-md:hidden">
              <div v-if="item.retention_due" class="min-w-0">
                <div class="text-ink-gray-7">{{ date(item.retention_due) }}</div>
                <div class="truncate text-sm text-ink-gray-5">{{ __("Retention") }}</div>
              </div>
              <span v-else :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ date(item.due) }}</span>
            </ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="STATUS[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ money(item.total, item.currency) }}</ListCell>
            <ListCell class="justify-end tabular-nums max-md:hidden" :class="item.outstanding ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ money(item.outstanding, item.currency) }}</ListCell>
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
import { Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Section, __, call, date, emailRecord, followList, go, money, monthName, newDoc, onedesk } from "../kit";

const props = defineProps({ projectName: { type: String, required: true }, projectTitle: String, kind: String, customer: String, currency: String });

// ERPNext's own colours for an invoice's status.
const STATUS = { Paid: "green", "Partly Paid": "blue", Unpaid: "orange", Overdue: "red", Draft: "red", Return: "gray", "Credit Note Issued": "gray" };
const said = ref(null);
const amount = (value) => money(value, props.currency);

async function load() {
  said.value = await call("onedesk.one_project.billing.invoices", { project: props.projectName });
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
    { title: __("Invoiced"), value: amount(t.invoiced), note: t.drafts ? __("{0} drafts", [t.drafts]) : "" },
    { title: __("Paid"), value: amount(t.paid), bar: share(t.paid, t.invoiced), note: t.advance ? __("{0} paid in advance", [amount(t.advance)]) : "" },
    { title: __("Outstanding"), value: amount(t.outstanding) },
    { title: __("Overdue"), value: amount(t.overdue), alarm: t.overdue > 0 },
    ...(t.retention ? [{ title: __("Retention Held"), value: amount(t.retention) }] : []),
  ];
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
  if (item.status !== "Draft") found.push({ label: __("Send"), icon: "lucide-send", onClick: () => send(item) });
  return found;
}
async function pay(item) {
  const verb = await call("onedesk.one.head.offer", { doctype: "Sales Invoice", name: item.name, verb: "invoice.record_payment" });
  if (verb) onedesk().head.act({ doctype: "Sales Invoice", doc: { name: item.name }, reload_doc: load }, verb);
}
const send = (item) => emailRecord("Sales Invoice", item.name);

const newInvoice = () => newDoc("Sales Invoice", { customer: props.customer, project: props.projectName });
const invoiceMonth = () =>
  onedesk().project.invoice_month({ doctype: "Project", doc: { name: props.projectName, project_name: props.projectTitle, customer: props.customer } });
</script>
