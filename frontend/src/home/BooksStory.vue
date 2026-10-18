<template>
  <div ref="root" class="pb-12">
    <div v-if="needs.length" class="mt-5 flex flex-wrap gap-2">
      <Button v-for="one in needs" :key="one.key" variant="outline" :label="one.label" @click="$emit('today')">
        <template #prefix><span :class="[one.icon, TONE[one.tone]]" class="size-4" aria-hidden="true" /></template>
      </Button>
    </div>

    <Section v-if="story.money" :title="__('Cash and Profit')" icon="lucide-wallet" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard class="h-96">
          <BarChart :title="__('Cash Flow')" :data="story.money.flow" x="month" :y="['inflow', 'outflow']" stacked :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="flowSeries" :reference-lines="[{ value: 0 }]" @select="go('/desk/query-report/Cash Flow')" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('Profit and Loss')" :data="story.money.profit" x="month" :y="['profit', 'loss']" stacked :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="profitSeries" :reference-lines="[{ value: 0 }]" @select="go('/desk/query-report/Profit and Loss Statement')" />
        </ChartCard>
        <ChartCard v-if="story.money.expenses.length" class="h-96">
          <DonutChart :title="__('Top Expenses')" :data="story.money.expenses" category="name" value="spent" :format="cash" :center-label="__('Total Expense')" :palette="ramp(6)" @select="(one) => expense(one.rows[0])" />
        </ChartCard>
      </div>
    </Section>

    <Section v-for="side in sides" :key="side.key" :title="side.title" :icon="side.icon" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard class="h-96">
          <BarChart :title="__('Ageing')" :data="side.ages" x="band" y="owed" split-by="band" stacked :y-axis="{ format: cash }" :palette="ageColors" @select="go(side.report)" />
        </ChartCard>
        <ChartCard v-if="side.parties.length" class="h-96">
          <BarChart :title="side.partiesTitle" :data="side.parties" x="name" :y="['owed']" horizontal :x-axis="wrap" :y-axis="{ format: cash }" :series-config="{ owed: { label: __('Outstanding Amount'), color: hue(side.hue) } }" @select="(one) => go(`${side.party}/${encodeURIComponent(one.row.name)}`)" />
        </ChartCard>
        <ChartCard v-if="side.statuses.length" class="h-96">
          <DonutChart :title="side.statusesTitle" :data="side.statuses" category="label" value="billed" :format="cash" variant="half" :center-label="__('Grand Total')" :palette="side.statusColors" @select="(one) => go(`${side.list}?status=${encodeURIComponent(one.rows[0].status)}`)" />
        </ChartCard>
      </div>
    </Section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { BarChart, ChartCard, DonutChart, useChartTokens } from "frappe-ui/charts";

import { Section, __, go, money, shortMonth } from "../kit";

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
const wrap = { echartOptions: { axisLabel: { formatter: (value) => value, overflow: "break" } } };

const flowSeries = computed(() => ({
  inflow: { label: __("Inflow"), color: hue(2) },
  outflow: { label: __("Outflow"), color: hue(8) },
}));
const profitSeries = computed(() => ({
  profit: { label: __("Profit"), color: hue(2) },
  loss: { label: __("Loss"), color: hue(8) },
}));

function expense(row) {
  if (!row?.account) return go("/desk/query-report/Profit and Loss Statement");
  go(`/desk/query-report/General Ledger?account=${encodeURIComponent(JSON.stringify([row.account]))}`);
}

const BANDS = () => ({ not_due: __("Not Yet Due") });
const ageColors = computed(() => {
  const seq = tokens.value.sequential;
  return [seq[6], seq[5], seq[4], seq[2], seq[1], seq[0]];
});

const STATUS = { Paid: 2, "Partly Paid": 0, Unpaid: 6, Overdue: 8 };
const statusHue = (status) => (status in STATUS ? hue(STATUS[status]) : tokens.value.axisLabel);

const side = (said, key) => ({
  ages: said.ages.map((one) => ({ band: BANDS()[one.band] || one.band, owed: one.owed })),
  parties: said.parties,
  statuses: said.statuses.map((one) => ({ ...one, label: __(one.status) })),
  statusColors: said.statuses.map((one) => statusHue(one.status)),
  key,
});

const sides = computed(() =>
  [
    props.story.receivable && {
      ...side(props.story.receivable, "receivable"),
      title: __("Accounts Receivable"),
      icon: "lucide-arrow-down-left",
      report: "/desk/query-report/Accounts Receivable",
      partiesTitle: __("Outstanding by Customer"),
      party: "/desk/customer",
      statusesTitle: __("Sales Invoice by Status"),
      list: "/desk/sales-invoice",
      hue: 2,
    },
    props.story.payable && {
      ...side(props.story.payable, "payable"),
      title: __("Accounts Payable"),
      icon: "lucide-arrow-up-right",
      report: "/desk/query-report/Accounts Payable",
      partiesTitle: __("Outstanding by Supplier"),
      party: "/desk/supplier",
      statusesTitle: __("Purchase Invoice by Status"),
      list: "/desk/purchase-invoice",
      hue: 6,
    },
  ].filter(Boolean)
);
</script>
