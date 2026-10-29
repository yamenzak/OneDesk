<template>
  <div class="grid gap-x-10 pb-12 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
    <PlaceSpot :said="spot" class="mb-4" />
    <template v-if="making.made_here">
      <Section v-if="making.boms.length" :title="__('Made From')" icon="lucide-list-tree" :aside="said.made ? said.made.name : ''" :action="said.made ? { icon: 'lucide-arrow-up-right', label: __('Bill of Materials'), onClick: () => go(`/desk/bom/${encodeURIComponent(said.made.name)}`) } : null">
        <p v-if="making.can_make" class="mb-2 text-base" :class="making.can_make.qty ? 'text-ink-gray-7' : 'text-ink-red-4'">
          {{ making.can_make.qty ? __("Enough for {0}. {1} runs out first.", [quantity(making.can_make.qty, said.stock_uom), making.can_make.limit]) : __("Not enough {0} for one", [making.can_make.limit]) }}
        </p>
        <Rows :rows="materials" :empty="__('No default bill of materials')" />
      </Section>
      <Section v-if="making.steps.length" :title="__('Steps')" icon="lucide-list-ordered" :aside="making.steps.length">
        <Rows :rows="steps" />
        <p v-if="said.made && bom" class="mt-2 text-sm text-ink-gray-5">
          {{ __("For {0}, {1} of materials and {2} of steps, {3} in all", [quantity(said.made.quantity, said.stock_uom), money(bom.raw_material_cost, bom.currency), money(bom.operating_cost, bom.currency), money(bom.total_cost, bom.currency)]) }}
        </p>
      </Section>
      <Section :title="__('Being Made')" icon="lucide-hammer" :aside="making.orders.length || ''" :action="said.made && said.can['Work Order'] && !said.disabled ? { text: true, icon: 'lucide-plus', label: __('Make More'), onClick: () => onedesk().item.make(said.name, said.made.name) } : null">
        <Rows :rows="orders" :empty="__('Nothing being made')" />
      </Section>
      <Section v-if="making.made.length" :title="__('Made, Last 12 Months')" icon="lucide-package-check" :aside="quantity(madeQty, said.stock_uom)">
        <Rows :rows="made" />
      </Section>
    </template>
    <Section v-if="making.used_in.length" :title="__('Goes Into')" icon="lucide-git-merge" :aside="making.used_in.length">
      <Rows :rows="usedIn" />
    </Section>
    <Section v-if="making.needed.length" :title="__('Needed for Making')" icon="lucide-clipboard-list" :aside="quantity(neededQty, said.stock_uom)">
      <Rows :rows="needed" />
    </Section>
    <Section v-if="making.made_here || making.boms.length" :title="__('Bills of Materials')" icon="lucide-file-stack" :aside="making.boms.length || ''" :action="said.can.BOM ? { text: true, icon: 'lucide-plus', label: __('New Bill of Materials'), onClick: () => onedesk().item.bom(said.name) } : null">
      <Rows :rows="boms" :empty="__('No bill of materials')" />
    </Section>
  </div>
    <aside class="min-w-0">
      <Section :title="__('Details')" icon="lucide-info">
        <Facts :facts="details" :form="form" @saved="emit('changed')" />
      </Section>
    </aside>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { Facts, PlaceSpot, Rows, Section, __, date, go, money, onedesk, quantity } from "../../kit";
import { usePlace } from "../../project/place";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const making = computed(() => props.said.making);
const uom = computed(() => props.said.stock_uom);
const bom = computed(() => making.value.boms.find((one) => one.name === props.said.made?.name) || null);
const madeQty = computed(() => making.value.made.reduce((sum, one) => sum + one.produced_qty, 0));
const neededQty = computed(() => making.value.needed.reduce((sum, one) => sum + one.left, 0));

const materials = computed(() =>
  making.value.materials.map((one, i) => ({
    key: `${one.item_code}-${i}`,
    label: one.item_name,
    sub: one.item_code !== one.item_name ? one.item_code : "",
    badge: making.value.can_make && one.covers === making.value.can_make.qty ? { label: __("Runs Out First"), theme: "amber" } : null,
    below: one.covers === null ? "" : one.covers ? __("Enough for {0}", [quantity(one.covers)]) : __("None free"),
    dim: quantity(one.qty, one.uom),
    value: money(one.amount, props.said.currency),
    route: `/desk/oneinventory/item/${encodeURIComponent(one.item_code)}?view=making`,
  }))
);

const steps = computed(() =>
  making.value.steps.map((one, i) => ({
    key: `${one.operation}-${i}`,
    label: __(one.operation),
    sub: one.workstation || "",
    dim: __("{0} min", [one.time_in_mins]),
    value: money(one.operating_cost, bom.value?.currency || props.said.currency),
    route: one.workstation ? `/desk/workstation/${encodeURIComponent(one.workstation)}` : `/desk/operation/${encodeURIComponent(one.operation)}`,
  }))
);

const orders = computed(() =>
  making.value.orders.map((one) => ({
    key: one.name,
    label: one.project_name || one.name,
    sub: one.project_name ? one.name : "",
    dot: one.late ? "red" : undefined,
    dim: __("{0} of {1} made", [quantity(one.produced_qty), quantity(one.qty)]),
    progress: one.qty ? Math.round((100 * one.produced_qty) / one.qty) : 0,
    below: one.expected_delivery_date ? (one.late ? __("Was wanted by {0}", [date(one.expected_delivery_date)]) : __("Wanted by {0}", [date(one.expected_delivery_date)])) : "",
    lines: one.steps.length ? [one.steps.map((step) => `${__(step.operation)} ${quantity(step.completed_qty)}`).join(" · ")] : [],
    value: __(one.status),
    route: `/desk/work-order/${encodeURIComponent(one.name)}`,
    actions: [
      making.value.can["Stock Entry"] && one.can_finish > 0 && { label: __("Finish"), icon: "lucide-package-check", onClick: () => onedesk().item.finish(one.name, one.can_finish) },
      making.value.can.shop_floor && one.steps.some((step) => step.completed_qty < one.qty) && { label: __("Open on Shop Floor"), icon: "lucide-factory", onClick: () => go(`/desk/floor?work_order=${encodeURIComponent(one.name)}`) },
    ].filter(Boolean),
  }))
);

const made = computed(() =>
  making.value.made.map((one) => ({
    key: one.name,
    label: one.project_name || one.name,
    sub: one.project_name ? one.name : "",
    dim: one.actual_end_date ? date(one.actual_end_date) : "",
    value: quantity(one.produced_qty, uom.value),
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
    value: quantity(one.qty, uom.value),
    route: `/desk/oneinventory/item/${encodeURIComponent(one.item)}?view=making`,
  }))
);

const needed = computed(() =>
  making.value.needed.map((one) => ({
    key: one.name,
    label: one.item_name,
    sub: one.name,
    below: one.project_name || "",
    value: __("{0} still to take", [quantity(one.left, uom.value)]),
    route: `/desk/work-order/${encodeURIComponent(one.name)}`,
  }))
);

const spot = usePlace("oneinventory_item.making", () => ({
  item: { name: props.said.name, item_name: props.said.item_name },
  making: {
    bom: props.said.made?.name || null,
    orders: making.value.orders.length,
    can_make: making.value.can_make?.qty ?? null,
    runs_out_first: making.value.can_make?.limit || null,
  },
}));

const details = computed(() => [
  ...(making.value.used_in.length || !making.value.made_here ? [{ label: __("Include Item In Manufacturing"), field: "include_item_in_manufacturing" }] : []),
  ...(making.value.made_here ? [{ label: __("Default BOM"), field: "default_bom" }] : []),
]);
</script>
