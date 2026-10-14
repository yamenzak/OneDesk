<template>
  <!-- Where the item is kept: each warehouse with what it holds, what is
       promised from it and on its way to it, and its reorder level; then its
       lots or numbered pieces, and the last moves in and out of it. -->
  <div class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('Where It Is')" icon="lucide-warehouse" :aside="said.stock.places.length || ''">
      <ItemPlaces :said="said" :form="form" @changed="emit('changed')" />
    </Section>
    <!-- Its lots and numbered pieces, as the Lots page shows them (frontend/src/lots). -->
    <Section v-if="said.has_batch_no" :title="__('Lots')" icon="lucide-boxes" :aside="said.stock.batches.length || ''" :action="lotAction">
      <LotRows :lots="said.stock.batches" :with-item="false" :empty="__('No lots in stock')" />
    </Section>
    <Section v-if="said.has_serial_no" :title="__('Serial Numbers')" icon="lucide-hash" :aside="said.stock.numbers.length || ''" :action="{ icon: 'lucide-arrow-up-right', label: __('Lots'), onClick: () => go(`/desk/lots?view=serials&item=${encodeURIComponent(said.name)}`) }">
      <SerialRows :serials="said.stock.numbers" :with-item="false" :empty="__('No numbered pieces yet')" />
    </Section>
    <button v-if="canTrack" type="button" class="mt-3 text-sm text-ink-gray-5 hover:underline" @click="onedesk().lots.track(said.name, () => emit('changed'))">{{ __("Track by Batch or Serial No") }}</button>
    <Section :title="__('Last Moves')" icon="lucide-arrow-left-right" :action="{ icon: 'lucide-arrow-up-right', label: __('Stock Ledger'), onClick: () => go(`/desk/query-report/Stock Ledger?item_code=${encodeURIComponent(said.name)}`) }">
      <Rows :rows="moves" :empty="__('No moves yet')" />
    </Section>
  </div>
    <!-- How the item is kept here: the item's own form fields, changed in place. -->
    <aside class="min-w-0">
      <Section :title="__('Details')" icon="lucide-info">
        <Facts :facts="details" :form="form" @saved="emit('changed')" />
      </Section>
    </aside>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { Facts, PlaceSpot, Rows, Section, __, can, date, go, onedesk, quantity } from "../kit";
import LotRows from "../lots/LotRows.vue";
import SerialRows from "../lots/SerialRows.vue";
import ItemPlaces from "./ItemPlaces.vue";
import { usePlace } from "../project/place";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const uom = computed(() => props.said.stock_uom);
const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");

// New Lot when the reader may make one, as the Lots page offers it.
const lotAction = computed(() =>
  can("create", "Batch") ? { text: true, icon: "lucide-plus", label: __("New Batch"), onClick: () => onedesk().lots.new_lot(props.said.name, () => emit("changed")) } : null
);
// An item not kept in lots yet, which hasn't moved, may be set up to be.
const canTrack = computed(() => !props.said.has_batch_no && !props.said.has_serial_no && !props.said.stock_exists && props.form.status("has_batch_no") === "Write");

// A move in plain words: what happened, to how much, and where.
function told(one) {
  const qty = quantity(Math.abs(one.actual_qty));
  if (one.from) return __("Moved {0} from {1} to {2}", [qty, one.from, one.to]);
  const into = one.actual_qty > 0;
  switch (one.purpose || one.voucher_type) {
    case "Material Issue":
      return one.project_name ? __("Used {0} on {1}", [qty, one.project_name]) : __("Used {0}", [qty]);
    case "Material Receipt":
      return __("Added {0}", [qty]);
    case "Material Transfer":
      return into ? __("Moved {0} in", [qty]) : __("Moved {0} out", [qty]);
    case "Manufacture":
      return into ? __("Made {0}", [qty]) : __("Used {0} in Making", [qty]);
    case "Material Transfer for Manufacture":
      return __("Sent {0} for Making", [qty]);
    case "Material Consumption for Manufacture":
      return __("Used {0} in Making", [qty]);
    case "Repack":
      return __("Repacked {0}", [qty]);
    case "Send to Subcontractor":
      return __("Sent {0} to Subcontractor", [qty]);
    case "Purchase Receipt":
    case "Purchase Invoice":
      return into ? __("Received {0}", [qty]) : __("Returned {0} to Supplier", [qty]);
    case "Delivery Note":
      return into ? __("Returned {0} by Customer", [qty]) : __("Delivered {0}", [qty]);
    case "Sales Invoice":
      return into ? __("Returned {0} by Customer", [qty]) : __("Sold {0}", [qty]);
    case "Subcontracting Receipt":
      return __("Received {0} from Subcontractor", [qty]);
    case "Stock Reconciliation":
      return __("Counted {0}", [quantity(one.qty_after_transaction)]);
    default:
      return `${__(one.kind)} ${into ? "+" : "−"}${qty}`;
  }
}

const moves = computed(() =>
  props.said.stock.moves.map((one, i) => ({
    key: `${one.voucher_no}-${i}`,
    label: told(one),
    sub: one.voucher_no,
    below: [
      date(one.posting_date),
      one.left
        ? __("{0} left in {1}, {2} in {3}", [quantity(one.left[0].qty), one.left[0].called, quantity(one.left[1].qty), one.left[1].called])
        : __("{0} left in {1}", [quantity(one.qty_after_transaction), one.called]),
      one.by && __("By {0}", [one.by]),
    ]
      .filter(Boolean)
      .join(" · "),
    dot: one.from ? "blue" : one.actual_qty > 0 ? "green" : "gray",
    route: `/desk/${slug(one.voucher_type)}/${encodeURIComponent(one.voucher_no)}`,
  }))
);

// The Stock view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.stock", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  stock: { places: props.said.stock.places.length, low_in: props.said.stock.places.filter((one) => one.low).map((one) => one.called), moves: props.said.stock.moves.length },
}));

// The item's own form fields that belong here, shown or locked as its form has them.
const details = [
  { label: __("Safety Stock"), field: "safety_stock" },
  { label: __("Allow Negative Stock"), field: "allow_negative_stock" },
  { label: __("Has Batch No"), field: "has_batch_no" },
  { label: __("Automatically Create New Batch"), field: "create_new_batch" },
  { label: __("Batch Number Series"), field: "batch_number_series" },
  { label: __("Has Expiry Date"), field: "has_expiry_date" },
  { label: __("Shelf Life In Days"), field: "shelf_life_in_days" },
  { label: __("Has Serial No"), field: "has_serial_no" },
  { label: __("Serial Number Series"), field: "serial_no_series" },
  { label: __("Warranty Period (in days)"), field: "warranty_period" },
  { label: __("Weight Per Unit"), field: "weight_per_unit" },
  { label: __("Weight UOM"), field: "weight_uom" },
];
</script>
