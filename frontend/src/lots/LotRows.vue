<template>
  <!-- Lots as a table, modelled on Odoo's Lots and Serial Numbers and Katana's
       batch tracking: the lot and its item, one status, when it was made and
       when it goes off, where it is, and how much is left (one_inventory/lots.py).
       The Lots page and an item's Stock tab both show them. -->
  <p v-if="!lots.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Lot") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell v-if="withItem" class="max-lg:hidden">{{ __("Made") }}</ListHeaderCell>
      <ListHeaderCell class="max-md:hidden">{{ __("Goes Off") }}</ListHeaderCell>
      <ListHeaderCell v-if="withItem" class="max-lg:hidden">{{ __("Where") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Left") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="lots" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/batch/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar v-if="withItem" :label="item.item_name" :image="item.image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.batch_id || item.name }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="status(item).label" :theme="status(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ withItem ? item.item_name : places(item) }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="status(item).label" :theme="status(item).theme" size="md" /></ListCell>
        <ListCell v-if="withItem" class="whitespace-nowrap text-base tabular-nums max-lg:hidden" :class="item.manufacturing_date ? 'text-ink-gray-7' : 'text-ink-gray-4'">
          {{ item.manufacturing_date ? date(item.manufacturing_date) : "–" }}
        </ListCell>
        <ListCell class="max-md:hidden">
          <div v-if="item.expiry_date" class="flex flex-col">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ date(item.expiry_date) }}</span>
            <span class="whitespace-nowrap text-sm" :class="item.state ? TEXT[item.state] : 'text-ink-gray-5'">{{ fromToday(item.expiry_date) }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell v-if="withItem" class="min-w-0 flex-wrap gap-1.5 max-lg:hidden">
          <Badge v-for="place in item.where || []" :key="place.warehouse" :label="`${place.label || place.warehouse} · ${quantity(place.qty)}`" theme="gray" size="sm" />
        </ListCell>
        <ListCell class="justify-end whitespace-nowrap tabular-nums">
          <span class="text-base text-ink-gray-8">{{ quantity(item.batch_qty) }}</span>
          <span class="ms-1 text-sm text-ink-gray-5">{{ __(item.stock_uom || item.uom || "") }}</span>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Badge } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, date, fromToday, go, quantity } from "../kit";

const props = defineProps({
  lots: { type: Array, required: true },
  // On an item's page the item's name is the page's, and not said again.
  withItem: { type: Boolean, default: true },
  empty: String,
});

// Phone: the lot and what is left; wider, its status, dates and where it is.
// On an item's page, a half-width column, where it is goes under the lot.
const columns = computed(() =>
  props.withItem
    ? {
        base: ["minmax(0,1fr)", "auto"],
        sm: ["minmax(0,1fr)", "7rem", "8rem"],
        md: ["minmax(0,1fr)", "7rem", "8rem", "8rem"],
        lg: ["minmax(0,1fr)", "7rem", "7rem", "8rem", "minmax(0,1.2fr)", "8rem"],
      }
    : { base: ["minmax(0,1fr)", "auto"], sm: ["minmax(0,1fr)", "6.5rem", "auto"], md: ["minmax(0,1fr)", "6.5rem", "7rem", "auto"] }
);
const places = (one) => (one.where || []).map((place) => `${place.label || place.warehouse} ${quantity(place.qty)}`).join(" · ");
const STATE = {
  Expired: { label: __("Gone Off"), theme: "red" },
  "Expiring Soon": { label: __("Going Off"), theme: "amber" },
};
const TEXT = { Expired: "text-ink-red-5", "Expiring Soon": "text-ink-amber-6" };
const status = (one) => STATE[one.state] || (one.expiry_date ? { label: __("Good"), theme: "green" } : { label: __("Keeps"), theme: "gray" });
</script>
