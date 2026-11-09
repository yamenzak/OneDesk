<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else ref="root">
      <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>

      <Section v-if="said.invoiced.length" :title="__('Revenue')" icon="lucide-receipt" data-cards>
        <ChartCard class="h-80">
          <BarChart :title="__('Invoiced by Month')" :data="said.invoiced" x="month" :y="['amount']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: invoicedMoney }" :series-config="{ amount: { label: __('Invoiced'), color: hue(0) } }" />
        </ChartCard>
      </Section>

      <Section v-if="said.margin !== null || said.priced.length" :title="__('Margin')" icon="lucide-percent" :action="{ text: true, label: __('Price Check'), onClick: () => go('/desk/query-report/Price Check') }" data-cards>
        <div class="grid gap-3 lg:grid-cols-3">
          <ChartCard class="h-96" :class="said.spent.length ? 'lg:col-span-2' : 'lg:col-span-3'">
            <BarChart :title="__('Margin at Worst')" :data="said.priced" x="name" :y="['margin']" horizontal :x-axis="wrapped" :y-axis="{ format: share }" :series-config="{ margin: { label: __('Margin'), color: hue(4) } }" :reference-lines="floorLine" />
          </ChartCard>
          <ChartCard v-if="said.spent.length" class="h-96">
            <DonutChart :title="__('What a Month Costs')" :data="said.spent" category="cost" value="amount" :format="listMoney" :center-label="said.currency" />
          </ChartCard>
        </div>
      </Section>

      <Section v-if="said.credits.length || said.models.length" :title="__('OneCredits')" icon="lucide-sparkles" :action="{ text: true, label: __('Credits'), onClick: () => go('/desk/credit-ledger-entry') }" data-cards>
        <div class="grid gap-3 lg:grid-cols-3">
          <ChartCard v-if="said.credits.length" class="h-80" :class="said.models.length ? 'lg:col-span-2' : 'lg:col-span-3'">
            <BarChart :title="__('Sold and Used by Month')" :data="said.credits" x="month" :y="['sold', 'used']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="CREDITS" />
          </ChartCard>
          <ChartCard v-if="said.models.length" class="h-80" :class="said.credits.length ? '' : 'lg:col-span-3'">
            <BarChart :title="__('By Model, Last 30 Days')" :data="said.models" x="model" :y="['credits']" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="{ credits: { label: __('OneCredits'), color: hue(2) } }" />
          </ChartCard>
        </div>
      </Section>

      <Section v-if="said.ai.length" :title="__('AI Usage')" icon="lucide-chart-column" :action="{ text: true, label: __('AI Usage'), onClick: () => go('/desk/query-report/AI Usage') }" data-cards>
        <div class="grid gap-3 lg:grid-cols-2">
          <ChartCard class="h-80">
            <AreaChart :title="__('Cost by Month')" :data="said.ai" x="month" :y="['cost']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: dollars }" :series-config="{ cost: { label: __('Cost'), color: hue(6) } }" />
          </ChartCard>
          <ChartCard class="h-80">
            <BarChart :title="__('Calls by Month')" :data="said.ai" x="month" :y="['calls']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ calls: { label: __('Calls'), color: hue(7) } }" />
          </ChartCard>
        </div>
      </Section>

      <Section v-if="said.plans.length" :title="__('Plans')" icon="lucide-tag" :action="{ text: true, label: __('Price List'), onClick: () => go('/desk/offering') }" data-cards>
        <div class="grid gap-3 lg:grid-cols-2">
          <ChartCard class="h-80">
            <BarChart :title="__('Workspaces by Plan')" :data="said.plans" x="plan" :y="['workspaces']" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="{ workspaces: { label: __('Workspaces'), color: hue(0) } }" />
          </ChartCard>
          <ChartCard class="h-80">
            <DonutChart :title="__('Monthly Revenue by Plan')" :data="said.plans" category="plan" value="revenue" :format="listMoney" :center-label="said.currency" />
          </ChartCard>
        </div>
      </Section>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { AreaChart, BarChart, ChartCard, DonutChart, NumberCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, Section, __, count, followList, get, go, money, shortMonth, wrapped } from "../kit";

const said = ref(null);
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const share = (value) => `${Math.round(value)}%`;
const listMoney = (value) => money(value, said.value.currency, 0);
const invoicedMoney = (value) => money(value, said.value.invoiced_in, 0);
const dollars = (value) => money(value, "USD", 2);

const load = async () => (said.value = await get("onedesk.one_admin.earnings.overview"));
load();
let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stops = ["Tenant", "Offering", "Workspace Server", "Credit Reservation", "Credit Ledger Entry", "Sales Invoice"].map((doctype) => followList(doctype, soon));
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearTimeout(timer);
});

const floorLine = computed(() => [{ value: said.value.floor, label: __("Floor"), dashed: true }]);
const CREDITS = computed(() => ({ sold: { label: __("Sold"), color: hue(0) }, used: { label: __("Used"), color: hue(4) } }));
const sparkline = (rows, key, type, at) => (rows.length > 1 ? { sparkline: { data: rows.map((one) => one[key]), type, color: hue(at) } } : {});
const marginDelta = () => (said.value.margin === null ? {} : { delta: Math.round(said.value.margin - said.value.floor), deltaSuffix: "%", deltaCaption: __("vs {0} floor", [share(said.value.floor)]) });
const cards = computed(() => [
  { key: "revenue", route: "/desk/tenant", props: { title: __("Monthly Revenue"), value: said.value.revenue, format: listMoney, ...sparkline(said.value.invoiced, "amount", "area", 0) } },
  ...(said.value.margin === null ? [] : [{ key: "margin", route: "/desk/query-report/Price Check", props: { title: __("Margin This Month"), value: said.value.margin, format: share, ...marginDelta() } }]),
  { key: "sold", route: "/desk/credit-ledger-entry", props: { title: __("OneCredits Sold This Month"), value: said.value.sold_now, format: count, ...sparkline(said.value.credits, "sold", "bar", 0) } },
  { key: "used", route: "/desk/query-report/AI Usage", props: { title: __("OneCredits Used This Month"), value: said.value.used_now, format: count, ...sparkline(said.value.credits, "used", "bar", 4) } },
]);
</script>
