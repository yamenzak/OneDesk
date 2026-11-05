<template>
  <div ref="root" class="pb-12">
    <div v-if="needs.length" class="mt-5 flex flex-wrap gap-2">
      <Button v-for="one in needs" :key="one.key" variant="outline" :label="one.label" @click="$emit('today')">
        <template #prefix><span :class="[one.icon, TONE[one.tone]]" class="size-4" aria-hidden="true" /></template>
      </Button>
    </div>

    <Section v-if="story.sales" :title="__('Selling')" icon="lucide-trending-up" data-cards>
      <ChartCard v-if="funnel.length" class="mb-3 h-72">
        <FunnelChart :title="__('Funnel Conversion')" :subtitle="__('Opportunities of the last 12 months')" :data="funnel" category="label" value="count" :format="count" @select="(one) => go(FUNNEL[one.row.step])" />
      </ChartCard>
      <div class="grid gap-3 lg:grid-cols-2">
        <ChartCard class="h-96">
          <LineChart :title="__('Sales Trend')" :data="story.sales.trend" x="month" :y="['leads', 'opportunities', 'won']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="trendSeries" @select="go('/desk/query-report/Lead Sources')" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('Forecasted Revenue')" :data="story.sales.forecast" x="month" :y="['won', 'forecast']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="forecastSeries" @select="go('/desk/query-report/Opportunity Forecast')" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="story.pipeline" :title="__('Sales Pipeline')" icon="lucide-kanban" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard v-if="stages.length" class="h-96">
          <BarChart :title="__('Opportunity by Sales Stage')" :data="stages" x="label" y="value" split-by="label" stacked :y-axis="{ format: cash }" :palette="stageColors" @select="(one) => stage(one.row)" />
        </ChartCard>
        <ChartCard v-if="story.pipeline.owners.length" class="h-96">
          <BarChart :title="__('Opportunity by Owner')" :data="story.pipeline.owners" x="name" :y="['open', 'won']" horizontal :x-axis="wrapped" :y-axis="{ format: cash }" :series-config="ownerSeries" @select="(one) => go(`/desk/opportunity?opportunity_owner=${encodeURIComponent(one.row.owner || '')}`)" />
        </ChartCard>
        <ChartCard v-if="story.pipeline.lost.length" class="h-96">
          <DonutChart :title="__('Lost Reasons')" :data="lost" category="label" value="count" :format="count" :center-label="__('Lost')" :palette="ramp(8)" @select="go('/desk/query-report/Won and Lost?group_by=Lost Reason')" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="story.sources" :title="__('Source')" icon="lucide-compass" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard v-if="story.sources.leads.length" class="h-96">
          <BarChart :title="__('Lead by Source')" :data="story.sources.leads" x="source" :y="['leads', 'converted']" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="sourceSeries" @select="(one) => go(`/desk/lead?utm_source=${encodeURIComponent(one.row.source)}`)" />
        </ChartCard>
        <ChartCard v-if="story.sources.won.length" class="h-96">
          <DonutChart :title="__('Won by Source')" :data="story.sources.won" category="name" value="won" :format="cash" :center-label="__('Won')" :palette="ramp(2)" @select="go('/desk/query-report/Won and Lost?group_by=Source')" />
        </ChartCard>
        <ChartCard v-if="story.sources.territories.length" class="h-96">
          <DonutChart :title="__('Opportunity by Territory')" :data="story.sources.territories" category="territory" value="value" :format="cash" variant="half" :center-label="__('Pipeline Value')" :palette="ramp(0)" @select="(one) => go(`/desk/opportunity?territory=${encodeURIComponent(one.rows[0].territory)}`)" />
        </ChartCard>
      </div>
    </Section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { BarChart, ChartCard, DonutChart, FunnelChart, LineChart, useChartTokens } from "frappe-ui/charts";

import { __, count, go, money, Section, shortMonth, wrapped } from "../kit";

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

const cash = (value) => money(value, props.story.currency, 0);
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));

const trendSeries = computed(() => ({
  leads: { label: __("Lead"), color: hue(0) },
  opportunities: { label: __("Opportunity"), color: hue(4) },
  won: { label: __("Won"), color: hue(2) },
}));
const forecastSeries = computed(() => ({
  won: { label: __("Won"), color: hue(2) },
  forecast: { label: __("Weighted Pipeline"), color: hue(0) },
}));
const ownerSeries = computed(() => ({
  open: { label: __("Pipeline Value"), color: hue(0) },
  won: { label: __("Won"), color: hue(2) },
}));
const sourceSeries = computed(() => ({
  leads: { label: __("Lead"), color: hue(0) },
  converted: { label: __("Converted"), color: hue(2) },
}));

const FUNNEL = {
  Opportunity: "/desk/opportunity",
  Quotation: '/desk/quotation?opportunity=["is","set"]',
  "Sales Order": "/desk/sales-order",
  "Sales Invoice": "/desk/sales-invoice",
  Paid: "/desk/sales-invoice?status=Paid",
};
const funnel = computed(() => (props.story.sales?.funnel || []).map((one) => ({ ...one, label: __(one.step) })));

const stages = computed(() => (props.story.pipeline?.stages || []).map((one) => ({ ...one, label: one.stage ? __(one.stage) : __("Not Recorded") })));
const stageColors = computed(() => {
  const seq = [...tokens.value.sequential].reverse();
  return stages.value.map((one, i) => (one.held ? hue(6) : seq[Math.min(i + 2, seq.length - 1)]));
});
function stage(row) {
  const open = encodeURIComponent(JSON.stringify(["in", ["Open", "Quotation", "Replied"]]));
  go(row?.stage ? `/desk/opportunity?sales_stage=${encodeURIComponent(row.stage)}&status=${open}` : `/desk/opportunity?status=${open}`);
}

const lost = computed(() => (props.story.pipeline?.lost || []).map((one) => ({ ...one, label: __(one.reason) })));
</script>
