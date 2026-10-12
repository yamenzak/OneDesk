<template>
  <!-- Who the item is bought from and at what, the quotes still open, what is
       on order and still to arrive, what has been asked for, who makes it,
       and its buying prices. Each starts the next document as its own form would. -->
  <div class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('Suppliers')" icon="lucide-truck" :aside="buying.suppliers.length || ''" :action="said.can_write ? { text: true, icon: 'lucide-plus', label: __('Add Supplier'), onClick: () => suppliersList?.add() } : null">
      <ItemSuppliers ref="suppliersList" :said="said" :form="form" @changed="emit('changed')" />
    </Section>
    <Section v-if="buying.quotes.length" :title="__('Quotes')" icon="lucide-message-square-quote" :aside="buying.quotes.length">
      <Rows :rows="quotes" />
    </Section>
    <Section :title="__('On Order')" icon="lucide-shopping-cart" :aside="buying.orders.length || ''" :action="said.can['Purchase Order'] && !said.disabled ? { text: true, icon: 'lucide-plus', label: __('Order More'), onClick: () => onedesk().item.order(said.name) } : null">
      <Rows :rows="orders" :empty="__('Nothing on order')" />
    </Section>
    <Section v-if="buying.requests.length" :title="__('Requested')" icon="lucide-clipboard-list" :aside="buying.requests.length">
      <Rows :rows="requests" />
    </Section>
    <Section v-if="buying.manufacturers.length || buying.can['Item Manufacturer']" :title="__('Manufacturers')" icon="lucide-factory" :aside="buying.manufacturers.length || ''" :action="buying.can['Item Manufacturer'] ? { text: true, icon: 'lucide-plus', label: __('Add Manufacturer'), onClick: () => onedesk().item.manufacturer(said.name) } : null">
      <div v-if="!buying.manufacturers.length" class="py-3 text-base text-ink-gray-5">{{ __("No manufacturer") }}</div>
      <ul v-else class="divide-y divide-outline-gray-1">
        <ItemManufacturerRow v-for="one in buying.manufacturers" :key="one.name" :maker="one" @changed="emit('changed')" />
      </ul>
    </Section>
    <Section :title="__('Buying Prices')" icon="lucide-tag" :action="said.can['Item Price'] ? { text: true, icon: 'lucide-plus', label: __('Set Price'), onClick: () => onedesk().item.price(said.name, true) } : null">
      <div v-if="!buying.prices.length" class="py-3 text-base text-ink-gray-5">{{ __("No buying price") }}</div>
      <ul v-else class="divide-y divide-outline-gray-1">
        <ItemPriceRow v-for="one in buying.prices" :key="one.name" :price="one" :last="buying.last_paid" :uom="said.stock_uom" @changed="emit('changed')" />
      </ul>
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
import { computed, ref } from "vue";

import { Facts, PlaceSpot, Rows, Section, __, date, money, onedesk, quantity } from "../kit";
import { usePlace } from "../project/place";
import ItemManufacturerRow from "./ItemManufacturerRow.vue";
import ItemPriceRow from "./ItemPriceRow.vue";
import ItemSuppliers from "./ItemSuppliers.vue";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const buying = computed(() => props.said.buying);
const uom = computed(() => props.said.stock_uom);
const suppliersList = ref();
const ours = computed(() => props.said.currency);
const defaultSupplier = computed(() => buying.value.suppliers.find((one) => one.default)?.supplier || null);

// ERPNext's own mappers, as each document's form makes the next one.
const MAPPERS = {
  receive: "erpnext.buying.doctype.purchase_order.mapper.make_purchase_receipt",
  order: "erpnext.stock.doctype.material_request.mapper.make_purchase_order",
  quote: "erpnext.buying.doctype.supplier_quotation.mapper.make_purchase_order",
};
// A request's order runs the order's link triggers, as the request's own form does.
const mapped = (kind, name, args) => onedesk().item.mapped(MAPPERS[kind], name, args, kind === "order");
const due = (one) => (one.due ? (one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)])) : "");

// A quote still open: who, at what in their currency, until when; the
// cheapest marked. Order This makes the order from it.
const quotes = computed(() =>
  buying.value.quotes.map((one) => ({
    key: one.name,
    label: one.supplier,
    sub: one.name,
    avatar: one.supplier,
    image: one.image,
    square: true,
    badge: one.cheapest ? { label: __("Cheapest"), theme: "green" } : null,
    dim: one.valid_till ? __("Until {0}", [date(one.valid_till)]) : "",
    value: `${money(one.rate, one.currency)} / ${__(one.uom)}`,
    under: one.currency !== ours.value ? money(one.base_rate, ours.value) : "",
    route: `/desk/supplier-quotation/${encodeURIComponent(one.name)}`,
    actions: props.said.can["Purchase Order"] ? [{ label: __("Order This"), icon: "lucide-shopping-cart", onClick: () => mapped("quote", one.name) }] : [],
  }))
);

// An order still to arrive: how much has, and Receive makes the receipt.
const orders = computed(() =>
  buying.value.orders.map((one) => ({
    key: one.name,
    label: one.party,
    sub: one.name,
    avatar: one.party,
    image: one.image,
    square: true,
    dot: one.late ? "red" : undefined,
    dim: due(one),
    value: __("{0} of {1} received", [quantity(one.done), quantity(one.qty, uom.value)]),
    route: `/desk/purchase-order/${encodeURIComponent(one.name)}`,
    actions: buying.value.can["Purchase Receipt"] ? [{ label: __("Receive"), icon: "lucide-package-check", onClick: () => mapped("receive", one.name) }] : [],
  }))
);

// What someone asked to be bought: who, for which project, and Make Order
// orders it from the default supplier, as the request's own form does.
const requests = computed(() =>
  buying.value.requests.map((one) => ({
    key: one.name,
    label: one.by ? __("Asked by {0}", [one.by]) : __(one.kind),
    sub: one.name,
    dot: one.late ? "red" : undefined,
    dim: due(one),
    below: one.project_name ? __("For {0}", [one.project_name]) : "",
    value: __("{0} to order", [quantity(one.left, uom.value)]),
    route: `/desk/material-request/${encodeURIComponent(one.name)}`,
    actions: props.said.can["Purchase Order"] ? [{ label: __("Make Order"), icon: "lucide-shopping-cart", onClick: () => mapped("order", one.name, { supplier: defaultSupplier.value }) }] : [],
  }))
);

// The Buying view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.buying", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  buying: {
    suppliers: buying.value.suppliers.map((one) => one.supplier),
    orders: buying.value.orders.length,
    late: buying.value.orders.filter((one) => one.late).length,
    quotes: buying.value.quotes.length,
  },
}));

// The item's own form fields that belong here, shown or locked as its form has them.
const details = [
  { label: __("Buying Unit"), field: "purchase_uom", placeholder: __("Same as stock") },
  { label: __("Lead Time in Days"), field: "lead_time_days" },
  { label: __("Minimum Order"), field: "min_order_qty" },
  { label: __("Over Receipt Allowance (%)"), field: "over_delivery_receipt_allowance" },
  { label: __("Supplied by the Customer"), field: "is_customer_provided_item" },
];
</script>
