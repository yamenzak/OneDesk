<template>
  <!-- What the item is made from, the work orders making it, its bills of
       materials, and what it goes into. -->
  <div class="pb-12">
    <PlaceSpot :said="spot" class="mb-4" />
    <Section v-if="making.boms.length" :title="__('Made From')" icon="lucide-list-tree" :aside="said.made ? said.made.name : ''" :action="said.made ? { icon: 'lucide-arrow-up-right', label: __('Bill of Materials'), onClick: () => go(`/desk/bom/${encodeURIComponent(said.made.name)}`) } : null">
      <Rows :rows="materials" :empty="__('No default bill of materials')" />
      <p v-if="said.made" class="mt-2 text-sm text-ink-gray-5">{{ __("For {0}, costing {1}", [quantity(said.made.quantity, said.stock_uom), money(said.made.total_cost, said.currency)]) }}</p>
    </Section>
    <Section :title="__('Being Made')" icon="lucide-hammer" :aside="making.orders.length || ''" :action="said.made && said.can['Work Order'] && !said.disabled ? { text: true, icon: 'lucide-plus', label: __('Make More'), onClick: () => onedesk().item.make(said.name, said.made.name) } : null">
      <Rows :rows="orders" :empty="__('Nothing being made')" />
    </Section>
    <Section :title="__('Bills of Materials')" icon="lucide-file-stack" :aside="making.boms.length || ''" :action="said.can.BOM ? { text: true, icon: 'lucide-plus', label: __('New Bill of Materials'), onClick: () => onedesk().item.bom(said.name) } : null">
      <Rows :rows="boms" :empty="__('No bill of materials')" />
    </Section>
    <Section v-if="making.used_in.length" :title="__('Goes Into')" icon="lucide-git-merge" :aside="making.used_in.length">
      <Rows :rows="usedIn" />
    </Section>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { PlaceSpot, Rows, Section, __, date, go, money, onedesk, quantity } from "../kit";
import { usePlace } from "../project/place";

const props = defineProps({ said: { type: Object, required: true } });
const making = computed(() => props.said.making);

const materials = computed(() =>
  making.value.materials.map((one, i) => ({
    key: `${one.item_code}-${i}`,
    label: one.item_name,
    sub: one.item_code !== one.item_name ? one.item_code : "",
    dim: quantity(one.qty, one.uom),
    value: money(one.amount, props.said.currency),
    route: `/desk/item/${encodeURIComponent(one.item_code)}`,
  }))
);

const orders = computed(() =>
  making.value.orders.map((one) => ({
    key: one.name,
    label: one.name,
    sub: one.project || "",
    dim: __("{0} of {1} made", [quantity(one.produced_qty), quantity(one.qty)]),
    progress: one.qty ? Math.round((100 * one.produced_qty) / one.qty) : 0,
    below: one.expected_delivery_date ? __("Wanted by {0}", [date(one.expected_delivery_date)]) : "",
    value: __(one.status),
    route: `/desk/work-order/${encodeURIComponent(one.name)}`,
  }))
);

const boms = computed(() =>
  making.value.boms.map((one) => ({
    key: one.name,
    label: one.name,
    badge: one.is_default ? __("Default") : !one.is_active ? { label: __("Not Active"), theme: "gray" } : one.docstatus === 0 ? { label: __("Draft"), theme: "gray" } : null,
    dim: one.project || "",
    value: money(one.total_cost, one.currency),
    route: `/desk/bom/${encodeURIComponent(one.name)}`,
  }))
);

const usedIn = computed(() =>
  making.value.used_in.map((one) => ({
    key: `${one.name}-${one.item}`,
    label: one.item_name,
    sub: one.name,
    value: quantity(one.qty, props.said.stock_uom),
    route: `/desk/item/${encodeURIComponent(one.item)}`,
  }))
);

// The Making view is a place (one_studio/places.py).
const spot = usePlace("oneinventory_item.making", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  making: { bom: props.said.made?.name || null, orders: making.value.orders.length },
}));
</script>
