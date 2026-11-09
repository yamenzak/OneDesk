<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else ref="root">
      <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <template v-if="shown === 'overview'">
        <Section :title="__('Workspaces')" icon="lucide-building-2" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-80 lg:col-span-2">
              <AreaChart :title="__('Workspaces by Month')" :data="growth" x="month" :y="['workspaces']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ workspaces: { label: __('Workspaces'), color: hue(0) } }" />
            </ChartCard>
            <ChartCard class="h-80">
              <DonutChart :title="__('By Status')" :data="said.status" category="status" value="workspaces" :format="count" :center-label="__('Workspaces')" />
            </ChartCard>
          </div>
        </Section>
        <Section :title="__('OneCredits')" icon="lucide-sparkles" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-80 lg:col-span-2">
              <BarChart :title="__('Used by Month')" :data="used" x="month" :y="['credits']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ credits: { label: __('OneCredits'), color: hue(4) } }" />
            </ChartCard>
            <ChartCard class="h-80">
              <BarChart :title="__('Most Used, Last 30 Days')" :data="said.spenders" x="name" y="credits" split-by="name" stacked horizontal :x-axis="wrapped" :y-axis="{ format: count }" />
            </ChartCard>
          </div>
        </Section>
        <Section :title="__('Servers')" icon="lucide-server" :action="{ text: true, label: __('All Servers'), onClick: () => go('/desk/oneadmin-servers') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-2">
            <ChartCard class="h-80">
              <BarChart :title="__('Memory and Disk Used')" :data="said.servers" x="server" :y="['memory', 'disk']" :y-axis="{ format: share }" :series-config="USE" />
            </ChartCard>
            <ChartCard class="h-80">
              <BarChart :title="__('Workspaces by Plan')" :data="said.plans" x="plan" y="workspaces" split-by="plan" stacked horizontal :x-axis="wrapped" :y-axis="{ format: count }" />
            </ChartCard>
          </div>
        </Section>
      </template>

      <template v-else>
        <p v-if="!said.needs.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-else :title="__('Needs You')" icon="lucide-triangle-alert" :aside="said.needs.length">
          <Rows :rows="needs" />
        </Section>
      </template>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { AreaChart, BarChart, ChartCard, DonutChart, NumberCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, Rows, Section, ViewTabs, __, call, count, followList, get, go, goTo, money, shortMonth, wrapped } from "../kit";

const said = ref(null);
const shown = ref("overview");
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const share = (value) => `${Math.round(value)}%`;
const USE = computed(() => ({ memory: { label: __("Memory"), color: hue(0) }, disk: { label: __("Disk"), color: hue(4) } }));

const load = async () => (said.value = await get("onedesk.one_admin.console.overview"));
load();
const stops = ["Tenant", "Offering", "Workspace Server", "Credit Reservation"].map((doctype) => followList(doctype, load));
onBeforeUnmount(() => stops.forEach((stop) => stop()));

const growth = computed(() => said.value.months.map((month, at) => ({ month, workspaces: said.value.joined[at] })));
const used = computed(() => said.value.months.map((month, at) => ({ month, credits: said.value.credits[at] })));
const views = computed(() => [
  { key: "overview", label: __("Overview") },
  { key: "needs", label: __("Needs You"), count: said.value.needs.length },
]);
const cards = computed(() => [
  { key: "live", route: "/desk/tenant", props: { title: __("Live Workspaces"), value: said.value.live, format: count, sparkline: { data: said.value.joined, type: "area", color: hue(0) } } },
  { key: "revenue", route: "/desk/tenant", props: { title: __("Monthly Revenue"), value: said.value.revenue, format: (value) => money(value, said.value.currency, 0) } },
  { key: "cost", route: "/desk/oneadmin-servers", props: { title: __("Server Cost a Month"), value: said.value.cost, format: (value) => `$${count(value)}` } },
  { key: "credits", route: "/desk/credit-ledger-entry", props: { title: __("OneCredits This Month"), value: said.value.credits.at(-1), format: count, sparkline: { data: said.value.credits, type: "bar", color: hue(4) } } },
]);
const needs = computed(() =>
  said.value.needs.map((one, at) => ({
    key: at,
    label: one.title,
    below: one.detail || one.why,
    badge: one.badge ? { label: one.badge, theme: "amber" } : null,
    onClick: () => (one.doctype ? goTo("Form", one.doctype, one.name) : null),
    actions: one.action ? [{ label: one.action.label, onClick: () => call(one.action.method, one.action.args).then(load) }] : [],
  }))
);
</script>
