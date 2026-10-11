<template>
  <!-- Where the item is kept: each warehouse with what it holds, what is
       promised from it and on its way to it, and its reorder level; then its
       batches, and the last moves in and out of it. -->
  <div class="pb-12">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('Where It Is')" icon="lucide-warehouse" :aside="said.stock.places.length || ''" :action="said.can_write ? { text: true, icon: 'lucide-pencil', label: __('Set Reorder Levels'), onClick: levels } : null">
      <Rows :rows="places" :empty="__('Not kept anywhere yet')" />
    </Section>
    <Section v-if="said.has_batch_no" :title="__('Batches')" icon="lucide-boxes" :aside="said.stock.batches.length || ''">
      <Rows :rows="batches" :empty="__('No batches in stock')" />
    </Section>
    <Section :title="__('Last Moves')" icon="lucide-arrow-left-right" :action="{ icon: 'lucide-arrow-up-right', label: __('Stock Ledger'), onClick: () => go(`/desk/query-report/Stock Ledger?item_code=${encodeURIComponent(said.name)}`) }">
      <Rows :rows="moves" :empty="__('No moves yet')" />
    </Section>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { PlaceSpot, Rows, Section, __, date, go, isPast, onedesk, quantity } from "../kit";
import { usePlace } from "../project/place";

const props = defineProps({ said: { type: Object, required: true } });
const uom = computed(() => props.said.stock_uom);
const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");

const places = computed(() =>
  props.said.stock.places.map((one) => ({
    key: one.warehouse,
    label: one.warehouse,
    dot: one.low ? "orange" : undefined,
    dim: [one.reserved && __("{0} promised", [quantity(one.reserved)]), one.ordered && __("{0} on order", [quantity(one.ordered)])].filter(Boolean).join(" · "),
    below: one.level ? (one.low ? __("Low, reorders at {0}, {1} at a time", [quantity(one.level), quantity(one.order_qty)]) : __("Reorders at {0}, {1} at a time", [quantity(one.level), quantity(one.order_qty)])) : "",
    value: quantity(one.on_hand, uom.value),
    route: `/desk/query-report/Stock Balance?item_code=${encodeURIComponent(props.said.name)}&warehouse=${encodeURIComponent(one.warehouse)}`,
  }))
);

const batches = computed(() =>
  props.said.stock.batches.map((one) => ({
    key: one.name,
    label: one.name,
    dot: one.expiry_date && isPast(one.expiry_date) ? "red" : undefined,
    dim: one.expiry_date ? __("Expires {0}", [date(one.expiry_date)]) : "",
    value: quantity(one.batch_qty, uom.value),
    route: `/desk/batch/${encodeURIComponent(one.name)}`,
  }))
);

const moves = computed(() =>
  props.said.stock.moves.map((one, i) => ({
    key: `${one.voucher_no}-${i}`,
    label: __(one.kind),
    sub: one.voucher_no,
    dim: date(one.posting_date),
    below: [__("{0} left in {1}", [quantity(one.qty_after_transaction), one.warehouse]), one.project].filter(Boolean).join(" · "),
    value: `${one.actual_qty > 0 ? "+" : ""}${quantity(one.actual_qty)}`,
    dot: one.actual_qty > 0 ? "green" : "gray",
    route: `/desk/${slug(one.voucher_type)}/${encodeURIComponent(one.voucher_no)}`,
  }))
);

const levels = () => onedesk().item.edit(props.said.name, props.said.modified, null, ["reorder_levels"]);

// The Stock view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.stock", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  stock: { places: props.said.stock.places.length, low_in: props.said.stock.places.filter((one) => one.low).map((one) => one.warehouse), moves: props.said.stock.moves.length },
}));
</script>
