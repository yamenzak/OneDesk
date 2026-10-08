<template>
  <!-- A retainer's months, newest first: the hours used of the allowance,
       any over, and the month's invoice or Invoice Month
       (one_project/retainer.py). -->
  <List :columns="{ base: ['minmax(0,1fr)', 'auto', 'auto'], md: ['8.5rem', 'minmax(6rem,1fr)', '7rem', '5.5rem', '9rem'] }" :row-height="48" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
    <ListRows :items="months.months" row-key="month" v-slot="{ item }">
      <ListRow v-bind="item.invoice?.name ? { onClick: () => go(`/desk/sales-invoice/${item.invoice.name}`) } : {}">
        <ListCell class="text-base text-ink-gray-8">{{ named(item.month) }}</ListCell>
        <ListCell class="max-md:hidden"><Progress v-if="months.allowance" :value="Math.min(100, Math.round((100 * item.hours) / months.allowance))" size="md" class="w-full" /></ListCell>
        <ListCell class="justify-end text-sm tabular-nums" :class="item.over ? 'text-ink-red-5' : 'text-ink-gray-7'">
          {{ months.allowance ? __("{0} of {1}", [hours(item.hours), hours(months.allowance)]) : hours(item.hours) }}
        </ListCell>
        <ListCell class="justify-end text-sm tabular-nums max-md:hidden" :class="item.over ? 'text-ink-red-5' : 'text-ink-gray-5'">
          {{ item.over ? __("{0} over", [hours(item.over)]) : "" }}
        </ListCell>
        <ListCell class="justify-end">
          <Badge v-if="item.invoice" :label="__(item.invoice.status)" :theme="STATUS[item.invoice.status] || 'gray'" size="md" />
          <span v-else-if="item.current" class="text-sm text-ink-gray-5">{{ __("This month") }}</span>
          <Button v-else-if="months.can_invoice" size="sm" :label="__('Invoice Month')" @click="$emit('invoice', item.month)" />
          <span v-else class="text-sm text-ink-gray-5">{{ __("Not invoiced") }}</span>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Badge, Button, Progress } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import { __, go, hours, monthName } from "../kit";

defineProps({ months: { type: Object, required: true } });
defineEmits(["invoice"]);

const STATUS = { Paid: "green", "Partly Paid": "blue", Unpaid: "orange", Overdue: "red", Draft: "gray" };
const named = (value) => monthName(value);
</script>
