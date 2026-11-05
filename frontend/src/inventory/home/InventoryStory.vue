<template>
  <div ref="root" class="pb-12">
    <div v-if="needs.length" class="mt-5 flex flex-wrap gap-2">
      <Button v-for="one in needs" :key="one.key" variant="outline" :label="one.label" @click="$emit('today')">
        <template #prefix><span :class="[one.icon, TONE[one.tone]]" class="size-4" aria-hidden="true" /></template>
      </Button>
    </div>

    <Section v-if="story.where" :title="__('Where Stock Is')" icon="lucide-warehouse" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard class="h-96">
          <DonutChart :title="__('By Warehouse')" :data="story.where.warehouses" category="name" value="worth" :format="cash" :center-label="__('Stock Value')" :palette="ramp(0)" @select="(one) => go(`/desk/stock-on-hand?warehouse=${encodeURIComponent(one.rows[0].warehouse)}`)" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('By Item Group')" :data="story.where.groups" x="name" y="worth" split-by="name" stacked horizontal :x-axis="wrapped" :y-axis="{ format: cash }" :palette="ramp(4)" @select="(one) => go(`/desk/item?item_group=${encodeURIComponent(one.row.group)}`)" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('Most Valuable Items')" :data="story.where.items" x="name" :y="['worth']" horizontal :x-axis="wrapped" :y-axis="{ format: cash }" :series-config="{ worth: { label: __('Stock Value'), color: hue(4) } }" @select="(one) => go(`/desk/item/${encodeURIComponent(one.row.item)}`)" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="story.moves" :title="__('How Stock Moves')" icon="lucide-arrow-left-right" data-cards>
      <div class="grid gap-3 lg:grid-cols-2">
        <ChartCard v-if="story.moves.worth" class="h-80">
          <AreaChart :title="__('Stock Value by Month')" :data="story.moves.worth" x="month" :y="['worth']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="{ worth: { label: __('Stock Value'), color: hue(0) } }" />
        </ChartCard>
        <ChartCard class="h-80">
          <BarChart :title="__('In and Out by Month')" :data="story.moves.flow" x="month" :y="FLOW" stacked :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="flowSeries" :reference-lines="[{ value: 0 }]" />
        </ChartCard>
      </div>
      <ChartCard v-if="story.moves.paths.length" class="mt-3 h-[30rem] overflow-x-auto">
        <div class="h-full min-w-[46rem]">
        <SankeyChart :title="__('Where Goods Came From and Went')" :data="story.moves.paths" source="from" target="to" value="worth" :format="cash" :echart-options="sankeyRoom" :palette="ramp(2)" />
        </div>
      </ChartCard>
      <div class="mt-3 grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <ChartCard class="h-80">
          <HeatmapChart :title="__('Busy Days')" :data="busyDays" x="month" y="day" value="moves" :x-axis="{ format: monthName }" :y-axis="{ format: dayName }" :format="count" palette="sequential" />
        </ChartCard>
        <ChartCard v-if="story.moves.kinds.length" class="h-80">
          <DonutChart :title="__('Papers by Kind')" :data="kinds" category="kind" value="papers" variant="half" :center-label="__('Papers')" :format="count" :palette="kindColors" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="ages.length" :title="__('How Old Stock Is')" icon="lucide-hourglass" data-cards>
      <ChartCard class="h-72">
        <BarChart :title="__('Stock Value by Age')" :data="ages" x="band" y="worth" split-by="band" stacked :y-axis="{ format: cash }" :palette="ageColors" @select="go('/desk/query-report/Stock Ageing')" />
      </ChartCard>
    </Section>

    <Section v-if="story.buying" :title="__('Buying')" icon="lucide-shopping-cart" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard v-if="requests.length" class="h-96">
          <FunnelChart :title="__('Material Requests')" :data="requests" category="step" value="requests" :format="count" :palette="ramp(2)" @select="go('/desk/material-request')" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('Bought by Supplier')" :data="suppliers" x="name" y="worth" split-by="name" stacked horizontal :x-axis="wrapped" :y-axis="{ format: cash }" :palette="ramp(6)" @select="(one) => go(`/desk/purchase-order?supplier=${encodeURIComponent(one.row.supplier)}`)" />
        </ChartCard>
        <ChartCard class="h-96">
          <ScatterChart :title="__('How Suppliers Keep to Dates')" :data="suppliers" x="worth" y="late" size="orders" split-by="name" label="name" :x-axis="{ title: __('Ordered'), format: cash }" :y-axis="{ title: __('Days Late'), format: days }" :palette="ramp(6)" />
        </ChartCard>
      </div>
    </Section>


    <Section v-if="equipment" :title="__('Equipment')" icon="lucide-truck" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard v-if="equipment.kinds.length" class="h-80">
          <BarChart :title="__('Value by Asset Category')" :data="equipment.kinds" x="kind" :y="['bought', 'now']" horizontal :x-axis="wrapped" :y-axis="{ format: cash }" :series-config="{ bought: { label: __('Total Asset Cost'), color: hue(0) }, now: { label: __('Value After Depreciation'), color: hue(1) } }" @select="(one) => go(`/desk/asset?asset_category=${encodeURIComponent(one.row.kind)}`)" />
        </ChartCard>
        <ChartCard v-if="equipment.statuses.length" class="h-80">
          <DonutChart :title="__('Assets by Status')" :data="equipment.statuses" category="label" value="assets" variant="half" :format="count" :center-label="__('Assets')" :palette="equipment.statusColors" @select="(one) => go(`/desk/asset?status=${encodeURIComponent(one.rows[0].status)}`)" />
        </ChartCard>
        <ChartCard v-if="equipment.services.length" class="h-80">
          <BarChart :title="__('Maintenance by Month')" :data="equipment.services" x="month" y="services" split-by="label" stacked :y-axis="{ format: count }" :x-axis="{ timeGrain: 'month', format: monthName }" :palette="equipment.serviceColors" @select="go('/desk/upkeep')" />
        </ChartCard>
      </div>
    </Section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { AreaChart, BarChart, ChartCard, DonutChart, FunnelChart, HeatmapChart, SankeyChart, ScatterChart, useChartTokens } from "frappe-ui/charts";

import { __, count, go, money, Section, shortMonth, weekdays, wrapped } from "../../kit";

const TONE = { late: "text-ink-red-5", soon: "text-ink-amber-6", left: "text-ink-gray-5" };

const props = defineProps({ story: { type: Object, required: true }, needs: { type: Array, default: () => [] } });
defineEmits(["today"]);

const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];
const ramp = (from) => {
  const all = tokens.value.categorical;
  return [...all.slice(from), ...all.slice(0, from)];
};
const STATUS = { good: 2, going: 0, late: 8, broken: 8 };
const statusHue = (tone) => (tone in STATUS ? hue(STATUS[tone]) : tokens.value.axisLabel);

const cash = (value) => money(value, props.story.currency, 0);


const sankeyRoom = computed(() => {
  const paths = props.story.moves?.paths || [];
  const from = new Set(paths.map((one) => one.from));
  const ends = {};
  for (const one of paths) if (!from.has(one.to)) ends[one.to] = (ends[one.to] || 0) + one.worth;
  const longest = Math.max(0, ...Object.entries(ends).map(([name, worth]) => `${name} · ${cash(worth)}`.length));
  return { media: [{ query: { minWidth: 0 }, option: { series: [{ right: Math.round(longest * 6.6) + 24 }] } }] };
});
const days = (value) => __("{0} d", [count(value)]);
const DAYS = () => [__("Monday"), __("Tuesday"), __("Wednesday"), __("Thursday"), __("Friday"), __("Saturday"), __("Sunday")];
const dayName = (value) => DAYS()[Number(value)] ?? value;
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const busyDays = computed(() => {
  const order = weekdays();
  return [...props.story.moves.days].sort((a, b) => (a.month < b.month ? -1 : a.month > b.month ? 1 : order.indexOf(a.day) - order.indexOf(b.day)));
});

const FLOW = ["bought", "received", "made", "delivered", "used", "counted"];
const flowSeries = computed(() => ({
  bought: { label: __("Bought"), color: hue(2) },
  received: { label: __("Received"), color: hue(3) },
  made: { label: __("Manufactured"), color: hue(0) },
  delivered: { label: __("Delivered"), color: hue(6) },
  used: { label: __("Material Issue"), color: hue(8) },
  counted: { label: __("Stock Reconciliation"), color: tokens.value.axisLabel },
}));

const KINDS = () => ({ bought: __("Bought"), received: __("Received"), made: __("Manufactured"), delivered: __("Delivered"), used: __("Material Issue"), counted: __("Stock Reconciliation"), moved: __("Material Transfer") });
const KIND_HUE = { bought: 2, received: 3, made: 0, delivered: 6, used: 8, counted: 5, moved: 1 };
const kinds = computed(() => props.story.moves.kinds.map((one) => ({ ...one, kind: KINDS()[one.kind] || one.kind })));
const kindColors = computed(() => props.story.moves.kinds.map((one) => hue(KIND_HUE[one.kind] ?? 9)));

const AGE_BANDS = () => [__("Up to 30 Days"), __("31 to 90 Days"), __("91 to 180 Days"), __("181 to 365 Days"), __("Over a Year")];
const ages = computed(() => (props.story.ages || []).map((one) => ({ band: AGE_BANDS()[one.band], worth: one.worth })));
const ageColors = computed(() => {
  const seq = tokens.value.sequential;
  return [seq[6], seq[4], seq[2], seq[1], seq[0]];
});

const STEPS = () => ({ asked: __("Requested"), ordered: __("Ordered"), arriving: __("To Receive"), here: __("Received") });
const requests = computed(() => (props.story.buying?.requests || []).map((one) => ({ step: STEPS()[one.step], requests: one.requests })));
const suppliers = computed(() => (props.story.buying?.suppliers || []).slice(0, 8));

const ASSET = { "Partially Depreciated": "going", "Fully Depreciated": "waiting", Submitted: "good", Sold: "waiting", Scrapped: "broken", "Out of Order": "broken", "In Maintenance": "late", Receipt: "going", "Capitalized": "good" };
const SERVICE = { Completed: "good", Planned: "going", Overdue: "late", Cancelled: "waiting" };
const tinted = (rows, tones) => ({
  rows: rows.map((one) => ({ ...one, label: __(one.status) })),
  colors: rows.map((one) => (statusHue(tones[one.status]))),
});

const equipment = computed(() => {
  const e = props.story.equipment;
  if (!e || !(e.kinds.length || e.statuses.length)) return null;
  const statuses = tinted(e.statuses, ASSET);
  const order = [...new Set(e.services.map((one) => one.status))];
  return {
    ...e,
    statuses: statuses.rows,
    statusColors: statuses.colors,
    services: e.services.map((one) => ({ ...one, label: __(one.status) })),
    serviceColors: order.map((status) => (statusHue(SERVICE[status]))),
  };
});

</script>
