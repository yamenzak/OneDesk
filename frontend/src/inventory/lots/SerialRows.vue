<template>
  <p v-if="!serials.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Serial No") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-md:hidden">{{ __("Where") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Batch No") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Warranty") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="serials" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/serial-no/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0">
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.serial_no || item.name }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="__(item.status || 'Inactive')" :theme="THEMES[item.status] || 'gray'" size="sm" class="sm:hidden" />
              <span v-if="withItem" class="truncate text-sm text-ink-gray-5">{{ item.item_name }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="__(item.status || 'Inactive')" :theme="THEMES[item.status] || 'gray'" size="md" /></ListCell>
        <ListCell class="min-w-0 truncate text-base max-md:hidden" :class="where(item) ? 'text-ink-gray-7' : 'text-ink-gray-4'">{{ where(item) || "–" }}</ListCell>
        <ListCell class="truncate text-base max-lg:hidden" :class="item.batch_no ? 'text-ink-gray-7' : 'text-ink-gray-4'">{{ item.batch_no || "–" }}</ListCell>
        <ListCell class="justify-end max-sm:hidden">
          <div v-if="item.warranty_expiry_date" class="flex flex-col items-end">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ date(item.warranty_expiry_date) }}</span>
            <span class="whitespace-nowrap text-sm" :class="isPast(item.warranty_expiry_date) ? 'text-ink-red-5' : 'text-ink-gray-5'">
              {{ isPast(item.warranty_expiry_date) ? __("Ended") : fromToday(item.warranty_expiry_date) }}
            </span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Badge } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, date, fromToday, go, isPast } from "../../kit";

defineProps({
  serials: { type: Array, required: true },
  withItem: { type: Boolean, default: true },
  empty: String,
});

const columns = {
  base: ["minmax(0,1fr)"],
  sm: ["minmax(0,1fr)", "7rem", "8rem"],
  md: ["minmax(0,1fr)", "7rem", "minmax(0,1fr)", "8rem"],
  lg: ["minmax(0,1fr)", "7rem", "minmax(0,1fr)", "8rem", "8rem"],
};
const THEMES = { Active: "green", Delivered: "blue", Expired: "red", Inactive: "gray", Consumed: "gray" };
const where = (one) => (one.status === "Delivered" && one.customer ? __("With {0}", [one.customer]) : one.warehouse_label || one.warehouse || "");
</script>
