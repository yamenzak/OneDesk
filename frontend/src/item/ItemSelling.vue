<template>
  <!-- What customers have ordered and not yet had and what of it can go now,
       the quotes still open, who buys the item and at what over the last
       twelve months, and its selling prices. Each starts the next document
       as its own form would. -->
  <div class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('To Deliver')" icon="lucide-package-check" :aside="selling.orders.length || ''">
      <Rows :rows="orders" :empty="__('Nothing to deliver')" />
    </Section>
    <Section v-if="selling.quotes.length" :title="__('Quotes')" icon="lucide-message-square-quote" :aside="selling.quotes.length">
      <Rows :rows="quotes" />
    </Section>
    <Section :title="__('Customers, Last 12 Months')" icon="lucide-users" :aside="selling.customers.length || ''">
      <ItemCustomers :said="said" :form="form" @changed="emit('changed')" />
    </Section>
    <Section :title="__('Selling Prices')" icon="lucide-tag" :action="said.can['Item Price'] ? { text: true, icon: 'lucide-plus', label: __('Set Price'), onClick: () => onedesk().item.price(said.name, false) } : null">
      <div v-if="!selling.prices.length" class="py-3 text-base text-ink-gray-5">{{ __("No selling price") }}</div>
      <ul v-else class="divide-y divide-outline-gray-1">
        <ItemPriceRow v-for="one in selling.prices" :key="one.name" :price="one" :sales="selling.sales" :uom="said.stock_uom" @changed="emit('changed')" />
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
import { computed } from "vue";

import { Facts, PlaceSpot, Rows, Section, __, date, money, onedesk, quantity } from "../kit";
import { usePlace } from "../project/place";
import ItemCustomers from "./ItemCustomers.vue";
import ItemPriceRow from "./ItemPriceRow.vue";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const selling = computed(() => props.said.selling);
const uom = computed(() => props.said.stock_uom);
const ours = computed(() => props.said.currency);

// ERPNext's own mappers, as each document's form makes the next one.
const MAPPERS = {
  deliver: "erpnext.selling.doctype.sales_order.mapper.make_delivery_note",
  invoice: "erpnext.selling.doctype.sales_order.mapper.make_sales_invoice",
  order: "erpnext.selling.doctype.quotation.mapper.make_sales_order",
};
const mapped = (kind, name) => onedesk().item.mapped(MAPPERS[kind], name);

// An order still to go: how much has, whether what is on hand covers it
// (soonest due first), and Deliver or Invoice makes the next document.
const orders = computed(() =>
  selling.value.orders.map((one) => ({
    key: one.name,
    label: one.party,
    avatar: one.party,
    image: one.image,
    square: true,
    dot: one.late ? "red" : undefined,
    dim: one.due ? (one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)])) : "",
    below: [one.name, one.project_name].filter(Boolean).join(" · "),
    badge: one.short === undefined ? null : one.short > 0 ? { label: __("{0} short", [quantity(one.short)]), theme: "orange" } : { label: __("Can Go Now"), theme: "green" },
    value: __("{0} of {1} delivered", [quantity(one.done), quantity(one.qty, uom.value)]),
    route: `/desk/sales-order/${encodeURIComponent(one.name)}`,
    actions: [
      selling.value.can["Delivery Note"] && one.left > 0 && { label: __("Deliver"), icon: "lucide-truck", onClick: () => mapped("deliver", one.name) },
      selling.value.can["Sales Invoice"] && one.to_bill && { label: __("Invoice"), icon: "lucide-receipt", onClick: () => mapped("invoice", one.name) },
    ].filter(Boolean),
  }))
);

// A quote still open: for whom, at what in their currency, until when (red
// when it runs out within a week). Make Order makes a customer's order from it.
const quotes = computed(() =>
  selling.value.quotes.map((one) => ({
    key: one.name,
    label: one.customer_name || one.party_name,
    sub: one.name,
    avatar: one.customer_name || one.party_name,
    image: one.image,
    square: true,
    dot: one.soon ? "red" : undefined,
    dim: one.valid_till ? __("Until {0}", [date(one.valid_till)]) : "",
    value: `${money(one.rate, one.currency)} / ${__(one.uom)}`,
    under: one.currency !== ours.value ? money(one.base_rate, ours.value) : "",
    route: `/desk/quotation/${encodeURIComponent(one.name)}`,
    actions: one.quotation_to === "Customer" && selling.value.can["Sales Order"] ? [{ label: __("Make Order"), icon: "lucide-shopping-cart", onClick: () => mapped("order", one.name) }] : [],
  }))
);

// The Selling view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.selling", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  selling: {
    orders: selling.value.orders.length,
    late: selling.value.orders.filter((one) => one.late).length,
    short: selling.value.orders.filter((one) => one.short > 0).length,
    quotes: selling.value.quotes.length,
    customers: selling.value.customers.map((one) => one.customer),
  },
}));

// The item's own form fields that belong here, shown or locked as its form has them.
const details = [
  { label: __("Selling Unit"), field: "sales_uom", placeholder: __("Same as stock") },
  { label: __("Maximum Discount (%)"), field: "max_discount", blankZero: true, placeholder: __("No limit") },
  { label: __("Over Billing Allowance (%)"), field: "over_billing_allowance" },
  { label: __("Earns Commission"), field: "grant_commission" },
];
</script>
