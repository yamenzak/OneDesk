<template>
  <!-- What customers have ordered and not yet had, who buys the item and for
       how much over the last twelve months, and its selling prices. -->
  <div class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('To Deliver')" icon="lucide-package-check" :aside="selling.orders.length || ''">
      <Rows :rows="orders" :empty="__('Nothing to deliver')" />
    </Section>
    <Section :title="__('Customers, Last 12 Months')" icon="lucide-users" :aside="selling.customers.length || ''">
      <Rows :rows="customers" :empty="__('Not sold in 12 months')" />
    </Section>
    <Section :title="__('Selling Prices')" icon="lucide-tag" :action="said.can['Item Price'] ? { text: true, icon: 'lucide-plus', label: __('Set Price'), onClick: () => onedesk().item.price(said.name, false) } : null">
      <Rows :rows="prices" :empty="__('No selling price')" />
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

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const selling = computed(() => props.said.selling);
const uom = computed(() => props.said.stock_uom);

const orders = computed(() =>
  selling.value.orders.map((one) => ({
    key: one.name,
    label: one.party,
    sub: one.name,
    dot: one.late ? "red" : undefined,
    dim: one.due ? (one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)])) : "",
    below: one.project || "",
    value: __("{0} to deliver", [quantity(one.left, uom.value)]),
    route: `/desk/sales-order/${encodeURIComponent(one.name)}`,
  }))
);

const customers = computed(() =>
  selling.value.customers.map((one) => ({
    key: one.customer,
    label: one.customer,
    dim: quantity(one.qty, uom.value),
    value: money(one.amount, props.said.currency),
    route: `/desk/customer/${encodeURIComponent(one.customer)}`,
  }))
);

const prices = computed(() =>
  selling.value.prices.map((one) => ({
    key: one.name,
    label: one.price_list,
    sub: one.customer || "",
    dim: one.valid_upto ? __("Until {0}", [date(one.valid_upto)]) : "",
    value: `${money(one.price_list_rate, one.currency)} / ${__(one.uom)}`,
    route: `/desk/item-price/${encodeURIComponent(one.name)}`,
  }))
);

// The Selling view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.selling", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  selling: { orders: selling.value.orders.length, late: selling.value.orders.filter((one) => one.late).length, customers: selling.value.customers.map((one) => one.customer) },
}));

// The item's own form fields that belong here, shown or locked as its form has them.
const details = [
  { label: __("Selling Unit"), field: "sales_uom" },
  { label: __("Maximum Discount (%)"), field: "max_discount" },
  { label: __("Over Billing Allowance (%)"), field: "over_billing_allowance" },
  { label: __("Earns Commission"), field: "grant_commission" },
];
</script>
