<template>
  <p v-if="!orders.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Work Order") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("At") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Manufactured Qty") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end max-lg:hidden">{{ __("Operations") }}</ListHeaderCell>
      <ListHeaderCell class="max-xl:hidden">{{ __("Expected Delivery Date") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="orders" row-key="name" v-slot="{ item }">
      <ListRow @click="emit('open', item.name)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.item_name || item.production_item" :image="item.item_image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.item_name || item.production_item }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="__(item.status)" :theme="THEMES[item.status] || 'gray'" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ [item.name, item.project_name].filter(Boolean).join(" · ") }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="__(item.status)" :theme="THEMES[item.status] || 'gray'" size="md" /></ListCell>
        <ListCell class="max-lg:hidden">
          <div v-if="item.current_operation" class="flex min-w-0 flex-col">
            <span class="truncate text-base text-ink-gray-7">{{ __(item.current_operation) }}</span>
            <span v-if="item.workstation_name" class="truncate text-sm text-ink-gray-5">{{ item.workstation_name }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell class="justify-end">
          <div class="flex w-full flex-col items-end gap-1.5">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ __("{0} of {1}", [quantity(item.produced_qty), quantity(item.qty)]) }}</span>
            <Progress :value="item.qty ? Math.min(100, Math.round((100 * item.produced_qty) / item.qty)) : 0" size="sm" class="w-full max-w-24" />
          </div>
        </ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums max-lg:hidden" :class="item.total_operations ? 'text-ink-gray-7' : 'text-ink-gray-4'">
          {{ item.total_operations ? __("{0} of {1}", [item.completed_operations, item.total_operations]) : "–" }}
        </ListCell>
        <ListCell class="max-xl:hidden">
          <div v-if="item.wanted" class="flex flex-col">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ date(item.wanted) }}</span>
            <span class="whitespace-nowrap text-sm" :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ fromToday(item.wanted) }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Avatar, Badge, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, date, fromToday, quantity } from "../../kit";

defineProps({ orders: { type: Array, required: true }, empty: String });
const emit = defineEmits(["open"]);

const columns = {
  base: ["minmax(0,1fr)", "6rem"],
  sm: ["minmax(0,1fr)", "8rem", "7rem"],
  lg: ["minmax(0,1fr)", "8rem", "minmax(0,12rem)", "7rem", "5rem"],
  xl: ["minmax(0,1fr)", "8rem", "minmax(0,12rem)", "7rem", "5rem", "8rem"],
};
const THEMES = { "In Process": "amber", "Not Started": "gray", Completed: "green", "Stock Reserved": "blue", "Stock Partially Reserved": "blue" };
</script>
