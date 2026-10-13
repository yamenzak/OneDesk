<template>
  <!-- Lots as rows: each with its number, what is left of it and where, when
       it was made and when it goes off, red once gone off and orange within
       a month (one_inventory/lots.py). The Lots page and an item's Stock tab
       both show them. -->
  <Rows :rows="rows" :empty="empty" />
</template>

<script setup>
import { computed } from "vue";

import { Rows, __, date, quantity } from "../kit";

const props = defineProps({
  lots: { type: Array, required: true },
  // On an item's page the item's name is the page's, and not said again.
  withItem: { type: Boolean, default: true },
  empty: String,
});

const DOTS = { Expired: "red", "Expiring Soon": "amber" };

const rows = computed(() =>
  props.lots.map((one) => ({
    key: one.name,
    label: props.withItem ? one.item_name : one.batch_id || one.name,
    sub: props.withItem ? one.batch_id || one.name : "",
    dot: DOTS[one.state],
    below: (one.where || []).map((place) => __("{0} in {1}", [quantity(place.qty), place.warehouse])).join(" · "),
    value: quantity(one.batch_qty, one.stock_uom || one.uom),
    under: when(one),
    route: `/desk/batch/${encodeURIComponent(one.name)}`,
  }))
);

function when(one) {
  if (!one.expiry_date) return one.manufacturing_date ? __("Made {0}", [date(one.manufacturing_date)]) : "";
  if (one.state === "Expired") return __("Went off {0}", [date(one.expiry_date)]);
  return __("Goes off {0}", [date(one.expiry_date)]);
}
</script>
