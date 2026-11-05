<template>
  <div class="grid gap-x-10" :class="facts ? 'pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]' : 'pb-2'">
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
    <aside v-if="facts" class="min-w-0">
      <Section :title="__('Details')" icon="lucide-info">
        <Facts :facts="details" :form="form" @saved="emit('changed')" />
      </Section>
    </aside>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { Facts, PlaceSpot, Rows, Section, __, date, money, onedesk, quantity } from "../../kit";
import { usePlace } from "../../project/place";
import ItemCustomers from "./ItemCustomers.vue";
import ItemPriceRow from "./ItemPriceRow.vue";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true }, facts: { type: Boolean, default: true } });
const emit = defineEmits(["changed"]);
const selling = computed(() => props.said.selling);
const uom = computed(() => props.said.stock_uom);
const ours = computed(() => props.said.currency);

const MAPPERS = {
  deliver: "erpnext.selling.doctype.sales_order.mapper.make_delivery_note",
  invoice: "erpnext.selling.doctype.sales_order.mapper.make_sales_invoice",
  order: "erpnext.selling.doctype.quotation.mapper.make_sales_order",
};
const mapped = (kind, name) => onedesk().item.mapped(MAPPERS[kind], name);

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
    badge: one.short === undefined ? null : one.short > 0 ? { label: __("{0} short", [quantity(one.short)]), theme: "amber" } : { label: __("Can Go Now"), theme: "green" },
    value: one.billed_only
      ? __("{0} of {1} billed", [quantity(one.qty - one.left), quantity(one.qty, uom.value)])
      : __("{0} of {1} delivered", [quantity(one.done), quantity(one.qty, uom.value)]),
    route: `/desk/sales-order/${encodeURIComponent(one.name)}`,
    actions: [
      selling.value.can["Delivery Note"] && !one.billed_only && one.left > 0 && { label: __("Deliver"), icon: "lucide-truck", onClick: () => mapped("deliver", one.name) },
      selling.value.can["Sales Invoice"] && one.to_bill && { label: __("Invoice"), icon: "lucide-receipt", onClick: () => mapped("invoice", one.name) },
    ].filter(Boolean),
  }))
);

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

const details = [
  { label: __("Default Sales Unit of Measure"), field: "sales_uom", placeholder: __("Same as stock") },
  { label: __("Max Discount (%)"), field: "max_discount", blankZero: true, placeholder: __("No limit") },
  { label: __("Over Billing Allowance (%)"), field: "over_billing_allowance" },
  { label: __("Grant Commission"), field: "grant_commission" },
];
</script>
