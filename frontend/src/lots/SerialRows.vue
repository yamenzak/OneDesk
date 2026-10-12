<template>
  <!-- Serial numbers as rows: each piece with where it is or who has it, its
       status as ERPNext keeps it, and its warranty (one_inventory/lots.py).
       The Lots page and an item's Stock tab both show them. -->
  <Rows :rows="rows" :empty="empty" />
</template>

<script setup>
import { computed } from "vue";

import { Rows, __, date, isPast } from "../kit";

const props = defineProps({
  serials: { type: Array, required: true },
  withItem: { type: Boolean, default: true },
  empty: String,
});

const THEMES = { Active: "green", Delivered: "blue", Expired: "red", Inactive: "gray", Consumed: "gray" };

const rows = computed(() =>
  props.serials.map((one) => ({
    key: one.name,
    label: one.serial_no || one.name,
    sub: props.withItem ? one.item_name : "",
    badge: { label: __(one.status || "Inactive"), theme: THEMES[one.status] || "gray" },
    below: one.status === "Delivered" && one.customer ? __("With {0}", [one.customer]) : one.warehouse || "",
    under: one.warranty_expiry_date
      ? isPast(one.warranty_expiry_date)
        ? __("Warranty ended {0}", [date(one.warranty_expiry_date)])
        : __("Warranty until {0}", [date(one.warranty_expiry_date)])
      : "",
    route: `/desk/serial-no/${encodeURIComponent(one.name)}`,
  }))
);
</script>
