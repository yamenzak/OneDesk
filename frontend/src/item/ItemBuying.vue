<template>
  <!-- Who the item is bought from and at what, what is on order and still to
       arrive, what has been asked for, and its buying prices. -->
  <div class="pb-12">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section :title="__('Suppliers')" icon="lucide-truck" :aside="buying.suppliers.length || ''">
      <Rows :rows="suppliers" :empty="__('Never bought')" />
    </Section>
    <Section :title="__('On Order')" icon="lucide-shopping-cart" :aside="buying.orders.length || ''" :action="said.can['Purchase Order'] && !said.disabled ? { text: true, icon: 'lucide-plus', label: __('Order More'), onClick: () => onedesk().item.order(said.name) } : null">
      <Rows :rows="open(buying.orders, 'purchase-order')" :empty="__('Nothing on order')" />
    </Section>
    <Section v-if="buying.requests.length" :title="__('Requested')" icon="lucide-clipboard-list" :aside="buying.requests.length">
      <Rows :rows="open(buying.requests, 'material-request')" />
    </Section>
    <Section :title="__('Buying Prices')" icon="lucide-tag" :action="said.can['Item Price'] ? { text: true, icon: 'lucide-plus', label: __('Set Price'), onClick: () => onedesk().item.price(said.name, true) } : null">
      <Rows :rows="prices(buying.prices)" :empty="__('No buying price')" />
    </Section>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { PlaceSpot, Rows, Section, __, date, money, onedesk, quantity } from "../kit";
import { usePlace } from "../project/place";

const props = defineProps({ said: { type: Object, required: true } });
const buying = computed(() => props.said.buying);

const suppliers = computed(() =>
  buying.value.suppliers.map((one) => ({
    key: one.supplier,
    label: one.supplier,
    badge: one.default ? __("Default") : null,
    dim: one.last ? __("Last ordered {0}", [date(one.last)]) : one.part_no ? __("Part {0}", [one.part_no]) : "",
    below: one.orders ? __("{0} on {1} orders", [quantity(one.qty, props.said.stock_uom), one.orders]) : "",
    value: one.rate !== null ? money(one.rate, props.said.currency) : "",
    route: `/desk/supplier/${encodeURIComponent(one.supplier)}`,
  }))
);

// An order or request still to be done: who it is with, when it is due, how
// many are still to come.
const open = (rows, slug) =>
  rows.map((one) => ({
    key: one.name,
    label: one.party || __(one.kind),
    sub: one.name,
    dot: one.late ? "red" : undefined,
    dim: one.due ? (one.late ? __("Was due {0}", [date(one.due)]) : __("Due {0}", [date(one.due)])) : "",
    value: __("{0} to come", [quantity(one.left, props.said.stock_uom)]),
    route: `/desk/${slug}/${encodeURIComponent(one.name)}`,
  }));

const prices = (rows) =>
  rows.map((one) => ({
    key: one.name,
    label: one.price_list,
    sub: one.supplier || one.customer || "",
    dim: one.valid_upto ? __("Until {0}", [date(one.valid_upto)]) : "",
    value: `${money(one.price_list_rate, one.currency)} / ${__(one.uom)}`,
    route: `/desk/item-price/${encodeURIComponent(one.name)}`,
  }));

// The Buying view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.buying", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  buying: { suppliers: buying.value.suppliers.map((one) => one.supplier), orders: buying.value.orders.length, late: buying.value.orders.filter((one) => one.late).length },
}));
</script>
