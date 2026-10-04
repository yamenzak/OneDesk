<template>
  <!-- The customer's invoices for the project and those under it, newest
       first (one_project/billing.py). -->
  <div class="pb-12 pt-2">
    <Loading v-if="!said" />
    <template v-else>
      <Section :title="__('Invoices')">
        <Figures :figures="figures" />
      </Section>

      <div class="mb-3 mt-5 flex items-center gap-2">
        <Button v-if="said.can_create" class="ms-auto" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Invoice')" @click="newInvoice" />
      </div>

      <div v-if="!said.invoices.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-receipt size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No invoices") }}</p>
      </div>
      <List v-else :columns="['minmax(10rem,1fr)', '7rem', '7rem', '8.5rem', '8rem', '8rem']" :row-height="44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Invoice") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Due") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Total") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Outstanding") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="said.invoices" row-key="name" v-slot="{ item }">
          <ListRow @click="go(`/desk/sales-invoice/${item.name}`)">
            <ListCell class="min-w-0"><span class="truncate text-ink-gray-8">{{ item.name }}</span></ListCell>
            <ListCell class="tabular-nums text-ink-gray-7">{{ date(item.date) }}</ListCell>
            <ListCell class="tabular-nums" :class="item.status === 'Overdue' ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ date(item.due) }}</ListCell>
            <ListCell><Badge :label="__(item.status)" :theme="STATUS[item.status] || 'gray'" size="md" /></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ money(item.total, item.currency) }}</ListCell>
            <ListCell class="justify-end tabular-nums" :class="item.outstanding ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ money(item.outstanding, item.currency) }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Badge, Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Section, __, call, date, followList, go, money, newDoc } from "../kit";

const props = defineProps({ projectName: { type: String, required: true }, customer: String, currency: String });

const STATUS = { Paid: "green", "Partly Paid": "blue", Unpaid: "orange", Overdue: "red", Draft: "gray" };
const said = ref(null);
const amount = (value) => money(value, props.currency);

async function load() {
  said.value = await call("onedesk.one_project.billing.invoices", { project: props.projectName });
}
let timer = null;
const stop = followList("Sales Invoice", () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
});
onBeforeUnmount(() => {
  stop();
  clearTimeout(timer);
});
watch(() => props.projectName, load, { immediate: true });

const figures = computed(() => {
  const t = said.value.totals;
  return [
    { title: __("Invoiced"), value: amount(t.invoiced), note: t.drafts ? __("{0} drafts", [t.drafts]) : "" },
    { title: __("Paid"), value: amount(t.paid), bar: t.invoiced ? Math.round((100 * t.paid) / t.invoiced) : undefined },
    { title: __("Outstanding"), value: amount(t.outstanding) },
    { title: __("Overdue"), value: amount(t.overdue), alarm: t.overdue > 0 },
  ];
});

const newInvoice = () => newDoc("Sales Invoice", { customer: props.customer, project: props.projectName });
</script>
