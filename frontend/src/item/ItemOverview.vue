<template>
  <!-- What the item is and how it moves: what left stock month by month, its
       description, its variants or its equipment on the left; the rest of
       what it is on the right, each with its value. -->
  <div ref="root" class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <div v-if="moved.length" data-cards class="pb-5">
        <ChartCard class="h-64">
          <BarChart :title="__('Out of Stock, Month by Month')" :subtitle="said.moved.said" :data="moved" x="month" :y="['qty']" :series-config="{ qty: { label: __('Out of Stock') } }" />
        </ChartCard>
      </div>

      <Section :title="__('Description')" icon="lucide-file-text" :action="said.can_write ? { icon: 'lucide-pencil', label: __('Edit Description'), onClick: describe } : null">
        <div v-if="described" class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.description" />
        <button v-else-if="said.can_write" class="text-base text-ink-gray-5 hover:text-ink-gray-8" @click="describe">{{ __("Add Description") }}</button>
        <p v-else class="text-base text-ink-gray-5">{{ __("No description") }}</p>
      </Section>

      <Section v-if="said.has_variants" :title="__('Variants')" icon="lucide-layers" :aside="said.variants.length || ''" :action="said.can.Item ? { text: true, icon: 'lucide-plus', label: __('Add Variant'), onClick: () => onedesk().item.variant(said.name) } : null">
        <Rows :rows="said.variants.map((one) => ({ key: one.name, label: one.item_name, sub: one.name !== one.item_name ? one.name : '', badge: one.disabled ? { label: __('Disabled'), theme: 'red' } : null, route: `/desk/item/${encodeURIComponent(one.name)}` }))" :empty="__('No variants')" />
      </Section>

      <Section v-if="said.assets" :title="__('Assets')" icon="lucide-monitor-smartphone" :aside="said.assets.length || ''" :action="{ icon: 'lucide-arrow-up-right', label: __('Assets'), onClick: () => go(`/desk/asset?item_code=${encodeURIComponent(said.name)}`) }">
        <Rows :rows="assets" :empty="__('No assets')" />
      </Section>
    </div>

    <aside class="flex min-w-0 flex-col">
      <Section :title="__('Details')" icon="lucide-info" :action="said.can_write ? { icon: 'lucide-pencil', label: __('Edit Details'), onClick: details } : null">
        <Facts v-if="details_.length" :facts="details_" />
        <p v-else class="text-base text-ink-gray-5">{{ __("Nothing") }}</p>
      </Section>
    </aside>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { BarChart, ChartCard } from "frappe-ui/charts";

import { Facts, Rows, Section, __, date, go, onedesk, quantity } from "../kit";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed", "view"]);
const root = ref();

// ERPNext writes the item's name as its description when none is given.
const described = computed(() => {
  const text = (props.said.description || "").replace(/<[^>]*>/g, "").trim();
  return Boolean(text) && text !== props.said.item_name && text !== props.said.item_code;
});
const moved = computed(() => {
  const m = props.said.moved;
  if (!m || !m.values.some(Boolean)) return [];
  return m.labels.map((month, i) => ({ month, qty: m.values[i] }));
});

const STATUS = { Draft: "gray", Submitted: "blue", "In Maintenance": "orange", "Out of Order": "red", Scrapped: "red", Sold: "gray" };
const assets = computed(() =>
  (props.said.assets || []).map((one) => ({
    key: one.name,
    label: one.asset_name,
    sub: one.name,
    dim: one.docstatus === 0 ? __("Not Yet Registered") : __(one.status),
    below: [one.location, one.custodian && __("With {0}", [one.custodian_name])].filter(Boolean).join(" · "),
    dot: STATUS[one.status] || "green",
    value: date(one.purchase_date),
    route: `/desk/asset/${encodeURIComponent(one.name)}`,
  }))
);

// The rest of what the item is, each only where it has a value.
const details_ = computed(() => {
  const s = props.said;
  const yes = (on, label) => (on ? label : null);
  const uses = [yes(s.is_purchase_item, __("Bought")), yes(s.is_sales_item, __("Sold")), yes(s.made, __("Made Here")), yes(s.is_sub_contracted_item, __("Made by a Subcontractor"))].filter(Boolean);
  return [
    uses.length && { label: __("Used For"), value: uses.join(", ") },
    s.lead_time_days && { label: __("Lead Time"), value: __("{0} days", [s.lead_time_days]) },
    s.min_order_qty && { label: __("Minimum Order"), value: quantity(s.min_order_qty, s.stock_uom) },
    s.safety_stock && { label: __("Safety Stock"), value: quantity(s.safety_stock, s.stock_uom) },
    s.has_batch_no && { label: __("Batches"), value: __("Kept by batch") },
    s.has_serial_no && { label: __("Serial Numbers"), value: s.stock?.serials !== null && s.stock?.serials !== undefined ? __("{0} in stock", [s.stock.serials]) : __("Kept by serial number") },
    s.asset_category && { label: __("Asset Category"), value: s.asset_category, route: `/desk/asset-category/${encodeURIComponent(s.asset_category)}` },
    // ERPNext sets 2099 when nobody gives one.
    s.end_of_life && !String(s.end_of_life).startsWith("2099") && { label: __("End of Life"), value: date(s.end_of_life) },
  ].filter(Boolean);
});

const details = () => onedesk().item.edit(props.said.name, props.said.modified, () => emit("changed"));
const describe = () => onedesk().item.edit(props.said.name, props.said.modified, () => emit("changed"), ["description"]);
</script>
