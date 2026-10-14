<template>
  <!-- Suppliers' quotes as a table, modelled on Odoo Purchase's list of
       vendor quotations: who quoted, where it stands, the request it answers, until
       when it holds and its total in its own money
       (one_inventory/quotes.py `quotes`). -->
  <p v-if="!quotes.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Supplier") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Request for Quotation") }}</ListHeaderCell>
      <ListHeaderCell class="max-md:hidden">{{ __("Valid Till") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Total") }}</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <ListRows :items="quotes" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/supplier-quotation/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.supplier_name || item.supplier" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.supplier_name || item.supplier }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="state(item).label" :theme="state(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ item.name }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="state(item).label" :theme="state(item).theme" size="md" /></ListCell>
        <ListCell class="max-lg:hidden">
          <div class="flex min-w-0 flex-col">
            <span class="truncate text-base text-ink-gray-7">{{ item.request || "–" }}</span>
            <span v-if="item.orders.length" class="truncate text-sm text-ink-gray-5">{{ __("Ordered as {0}", [andList(item.orders)]) }}</span>
          </div>
        </ListCell>
        <ListCell class="max-md:hidden">
          <div v-if="item.valid_till" class="flex flex-col">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ date(item.valid_till) }}</span>
            <span class="whitespace-nowrap text-sm" :class="item.status === 'Expired' ? 'text-ink-red-5' : item.expiring ? 'text-ink-amber-6' : 'text-ink-gray-5'">{{ fromToday(item.valid_till) }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ money(item.grand_total, item.currency) }}</ListCell>
        <ListCell class="justify-end" @click.stop>
          <Dropdown v-if="actions(item).length" :options="actions(item)" placement="right">
            <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, andList, date, fromToday, go, money, onedesk } from "../kit";

const props = defineProps({ quotes: { type: Array, required: true }, can: { type: Object, required: true }, empty: String });
const emit = defineEmits(["compare"]);

// The total is the one a phone keeps; the rest join as the page widens.
const columns = {
  base: ["minmax(0,1fr)", "auto", "2rem"],
  sm: ["minmax(0,1fr)", "8rem", "8rem", "2rem"],
  md: ["minmax(0,1fr)", "8rem", "8rem", "8rem", "2rem"],
  lg: ["minmax(0,1fr)", "8rem", "minmax(0,1fr)", "8rem", "8rem", "2rem"],
};

// ERPNext's own statuses, each with its colour.
const STATES = {
  Draft: [() => __("Draft"), "gray"],
  Submitted: [() => __("Submitted"), "blue"],
  "Partially Ordered": [() => __("Partially Ordered"), "green"],
  Ordered: [() => __("Ordered"), "green"],
  Expired: [() => __("Expired"), "red"],
  Stopped: [() => __("Stopped"), "gray"],
};
function state(one) {
  const [label, theme] = STATES[one.status] || [() => __(one.status), "gray"];
  return { label: label(), theme };
}

const actions = (one) =>
  [
    one.request && { label: __("Compare"), icon: "lucide-columns-3", onClick: () => emit("compare", one.request) },
    props.can.order && ["Submitted", "Partially Ordered"].includes(one.status) && { label: __("Order"), icon: "lucide-shopping-cart", onClick: () => onedesk().quotes.order(one.name) },
  ].filter(Boolean);
</script>
