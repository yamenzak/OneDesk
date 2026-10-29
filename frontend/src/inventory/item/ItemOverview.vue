<template>
  <div ref="root" class="pb-12">
  <Section v-if="needs.length" boxed class="!mt-0" :title="__('Needs You')" icon="lucide-bell" :aside="needs.length">
    <Rows :rows="needs" />
  </Section>
  <div class="grid gap-x-10 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <div v-if="moved.length" data-cards class="pb-5">
        <ChartCard class="h-64">
          <BarChart :title="__('Used and Sent Out, Month by Month')" :subtitle="said.moved.said" :data="moved" x="month" :y="['qty']" :y-axis="{ format: (value) => quantity(value, said.stock_uom) }" :series-config="{ qty: { label: __('Used and Sent Out') } }" />
        </ChartCard>
      </div>

      <Section :title="__('Description')" icon="lucide-file-text">
        <FieldEdit :form="form" field="description" start :label="__('Description')" :placeholder="said.can_write ? __('Add Description') : __('No description')" @saved="emit('changed')" />
      </Section>

      <Section v-if="said.has_variants" :title="__('Variants')" icon="lucide-layers" :aside="said.variants.length || ''" :action="said.can.Item ? [said.choices && { text: true, icon: 'lucide-list-plus', label: __('Make Several'), onClick: () => emit('several') }, { text: true, icon: 'lucide-plus', label: __('Add Variant'), onClick: () => onedesk().item.variant(said.name) }] : null">
        <Rows :rows="said.variants.map((one) => ({ key: one.name, label: one.item_name, sub: one.name !== one.item_name ? one.name : '', badge: one.disabled ? { label: __('Disabled'), theme: 'red' } : null, route: `/desk/item/${encodeURIComponent(one.name)}` }))" :empty="__('No variants')" />
      </Section>

      <Section v-if="said.assets" :title="__('Assets')" icon="lucide-monitor-smartphone" :aside="said.assets.length || ''" :action="{ icon: 'lucide-arrow-up-right', label: __('Assets'), onClick: () => go(`/desk/asset?item_code=${encodeURIComponent(said.name)}`) }">
        <Rows :rows="assets" :empty="__('No assets')" />
      </Section>
    </div>

    <aside class="flex min-w-0 flex-col">
      <Section :title="__('Details')" icon="lucide-info">
        <Facts :facts="details_" :form="form" @saved="emit('changed')" />
      </Section>
    </aside>
  </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { BarChart, ChartCard } from "frappe-ui/charts";

import { Facts, FieldEdit, Rows, Section, __, date, go, onedesk, quantity } from "../../kit";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed", "view", "several"]);
const root = ref();

const moved = computed(() => {
  const m = props.said.moved;
  if (!m || !m.values.some(Boolean)) return [];
  return m.labels.map((month, i) => ({ month, qty: m.values[i] }));
});

const STATUS = { Draft: "gray", Submitted: "blue", "In Maintenance": "amber", "Out of Order": "red", Scrapped: "red", Sold: "gray" };
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

const needs = computed(() => {
  const s = props.said;
  const uom = s.stock_uom;
  const rows = [];
  const today = new Date().toISOString().slice(0, 10);
  if (s.end_of_life && !String(s.end_of_life).startsWith("2099") && s.end_of_life <= today) {
    rows.push({ key: "ended", dot: "red", label: __("Past Its End of Life"), value: date(s.end_of_life) });
  }
  if (s.summary?.free < 0) {
    rows.push({ key: "short", dot: "red", label: __("{0} short", [quantity(-s.summary.free, uom)]), onClick: () => emit("view", "selling") });
  }
  for (const one of s.stock?.batches || []) {
    if (!one.state) continue;
    const past = one.state === "Expired";
    rows.push({
      key: `lot-${one.name}`,
      dot: past ? "red" : "amber",
      label: past ? __("Expired, Still in Stock") : __("Expiring Soon"),
      sub: one.batch_id || one.name,
      below: quantity(one.batch_qty, uom),
      value: past ? __("Expired {0}", [date(one.expiry_date)]) : __("Expires {0}", [date(one.expiry_date)]),
      route: `/desk/batch/${encodeURIComponent(one.name)}`,
    });
  }
  for (const one of s.stock?.places || []) {
    if (!one.low) continue;
    rows.push({ key: `low-${one.warehouse}`, dot: "amber", label: __("Running Low in {0}", [one.warehouse]), below: __("Reorders at {0}", [quantity(one.level, uom)]), value: __("{0} expected", [quantity(one.projected, uom)]), onClick: () => emit("view", "stock") });
  }
  for (const one of s.buying?.orders || []) {
    if (!one.late) continue;
    rows.push({ key: one.name, dot: "red", label: __("Late from {0}", [one.party]), sub: one.name, below: __("{0} still to come", [quantity(one.left, uom)]), value: __("Due {0}", [date(one.due)]), route: `/desk/purchase-order/${encodeURIComponent(one.name)}` });
  }
  for (const one of s.selling?.orders || []) {
    if (!one.late) continue;
    rows.push({ key: one.name, dot: "red", label: __("Late to {0}", [one.party]), sub: one.name, below: one.billed_only ? __("{0} still to bill", [quantity(one.left, uom)]) : __("{0} still to send", [quantity(one.left, uom)]), value: __("Due {0}", [date(one.due)]), route: `/desk/sales-order/${encodeURIComponent(one.name)}` });
  }
  for (const one of s.buying?.requests || []) {
    rows.push({ key: one.name, dot: "amber", label: __("Asked For, Not Yet Ordered"), sub: one.name, below: quantity(one.left, uom), value: __("Due {0}", [date(one.due)]), route: `/desk/material-request/${encodeURIComponent(one.name)}` });
  }
  return rows;
});

const details_ = computed(() => [
  { label: __("Sold by Size"), field: "one_measured_by" },
  { label: __("Size Unit"), field: "one_size_uom" },
  { label: __("Allow Purchase"), field: "is_purchase_item" },
  { label: __("Allow Sales"), field: "is_sales_item" },
  props.said.made && { label: __("Manufactured"), value: __("Yes") },
  { label: __("Is Subcontracted Item"), field: "is_sub_contracted_item" },
  { label: __("Country of Origin"), field: "country_of_origin" },
  { label: __("Customs Tariff Number"), field: "customs_tariff_number" },
  { label: __("Asset Category"), field: "asset_category" },
  { label: __("End of Life"), field: "end_of_life" },
].filter(Boolean));
</script>
