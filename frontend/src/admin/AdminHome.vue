<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else ref="root" class="pb-4">
      <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <template v-if="shown === 'overview'">
        <Section v-if="said.invoiced.length || said.plans.length" :title="__('Revenue')" icon="lucide-receipt" :action="{ text: true, label: __('Billing'), onClick: () => go('/desk/oneadmin-billing') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard v-if="said.invoiced.length" class="h-80" :class="said.plans.length ? 'lg:col-span-2' : 'lg:col-span-3'">
              <AreaChart :title="__('Paid by Month')" :data="said.invoiced" x="month" :y="['amount']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: paidMoney }" :series-config="{ amount: { label: __('Paid'), color: hue(0) } }" />
            </ChartCard>
            <ChartCard v-if="said.plans.length" class="h-80" :class="said.invoiced.length ? '' : 'lg:col-span-3'">
              <DonutChart :title="__('Monthly Revenue by Plan')" :data="said.plans" category="plan" value="revenue" :format="listMoney" :center-label="__('A Month')" />
            </ChartCard>
          </div>
        </Section>

        <Section v-if="said.funnel[0].signups" :title="__('Signups')" icon="lucide-user-plus" :action="{ text: true, label: __('All Signups'), onClick: () => go('/desk/account-request') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-80">
              <FunnelChart :title="__('Last 90 Days')" :data="said.funnel" category="stage" value="signups" :format="count" />
            </ChartCard>
            <ChartCard class="h-80 lg:col-span-2">
              <BarChart :title="__('Signups by Month')" :data="said.signups" x="month" :y="['started', 'paid']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="SIGNUPS" />
            </ChartCard>
          </div>
        </Section>

        <Section :title="__('Workspaces')" icon="lucide-building-2" :action="{ text: true, label: __('All Workspaces'), onClick: () => go('/desk/tenant') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-80 lg:col-span-2">
              <AreaChart :title="__('Workspaces by Month')" :data="growth" x="month" :y="['workspaces']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ workspaces: { label: __('Workspaces'), color: hue(0) } }" />
            </ChartCard>
            <ChartCard class="h-80">
              <DonutChart :title="__('By Status')" :data="said.status" category="status" value="workspaces" :format="count" :center-label="__('Workspaces')" />
            </ChartCard>
          </div>
        </Section>

        <Section :title="name('one_ai')" icon="lucide-sparkles" :action="{ text: true, label: __('AI Usage'), onClick: () => go('/desk/query-report/AI Usage') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-80">
              <BarChart :title="__('Credits Used by Month')" :data="used" x="month" :y="['credits']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ credits: { label: __('Credits'), color: hue(4) } }" />
            </ChartCard>
            <ChartCard class="h-80">
              <LineChart :title="__('Calls by Month')" :data="calls" x="month" :y="['calls']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: count }" :series-config="{ calls: { label: __('Calls'), color: hue(2) } }" />
            </ChartCard>
            <ChartCard class="h-80">
              <BarChart :title="__('Most Used, Last 30 Days')" :data="said.spenders" x="name" y="credits" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="{ credits: { label: __('Credits'), color: hue(4) } }" />
            </ChartCard>
          </div>
        </Section>

        <Section v-if="said.servers.length" :title="__('Servers')" icon="lucide-server" :action="{ text: true, label: __('All Servers'), onClick: () => go('/desk/workspace-server') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-2">
            <ChartCard class="h-80">
              <BarChart :title="__('Memory and Disk Used')" :data="said.servers" x="server" :y="['memory', 'disk']" :y-axis="{ min: 0, max: 100, format: share }" :series-config="USE" />
            </ChartCard>
            <ChartCard class="h-80">
              <BarChart :title="__('Workspaces and Room Left')" :data="room" x="server" :y="['workspaces', 'room']" stacked :y-axis="{ format: count }" :series-config="ROOM" />
            </ChartCard>
          </div>
        </Section>

        <Section :title="__('Health')" icon="lucide-heart-pulse" :action="{ text: true, label: __('Status'), onClick: () => go('/desk/oneadmin-status') }">
          <div class="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">
            <article v-for="one in said.health" :key="one.service" class="flex cursor-pointer items-center justify-between gap-2 rounded-4 border border-outline-gray-1 bg-surface-elevation-1 px-3 py-2 hover:border-outline-gray-3" role="link" tabindex="0" @click="go('/desk/oneadmin-status')" @keydown.enter="go('/desk/oneadmin-status')">
              <span class="truncate text-base text-ink-gray-8">{{ one.label }}</span>
              <Badge :label="__(one.state)" :theme="THEMES[one.state] || 'gray'" />
            </article>
          </div>
          <div v-if="said.errors.length || said.error_places.length" class="mt-3 grid gap-3 lg:grid-cols-3" data-cards>
            <ChartCard v-if="said.errors.length" class="h-72" :class="said.error_places.length ? 'lg:col-span-2' : 'lg:col-span-3'">
              <BarChart :title="__('New Errors by Day')" :data="said.errors" x="day" :y="['errors']" :x-axis="{ format: dayOf }" :y-axis="{ format: count }" :series-config="{ errors: { label: __('New Errors'), color: hue(6) } }" />
            </ChartCard>
            <ChartCard v-if="said.error_places.length" class="h-72" :class="said.errors.length ? '' : 'lg:col-span-3'">
              <BarChart :title="__('Open Errors by Workspace')" :data="said.error_places" x="name" y="errors" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="{ errors: { label: __('Times Seen'), color: hue(6) } }" />
            </ChartCard>
          </div>
        </Section>

        <Section v-if="said.rollout.releases.length" :title="__('Releases')" icon="lucide-rocket" :action="{ text: true, label: __('All Releases'), onClick: () => go('/desk/oneadmin-releases') }" data-cards>
          <div class="grid gap-3 lg:grid-cols-3">
            <ChartCard class="h-72">
              <DonutChart :title="__('Workspaces by Release')" :data="releases" category="release" value="workspaces" :format="count" :center-label="__('Workspaces')" />
            </ChartCard>
            <Figures :figures="rollout" :columns="2" class="content-start lg:col-span-2" />
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
import { Badge } from "frappe-ui";
import { AreaChart, BarChart, ChartCard, DonutChart, FunnelChart, LineChart, NumberCard, useChartTokens } from "frappe-ui/charts";

import { Figures, Loading, Page, Rows, Section, ViewTabs, __, call, count, followList, get, go, goTo, money, shortMonth, wrapped, name } from "../kit";

const THEMES = { Working: "green", Failing: "red", "Not Set Up": "gray" };
const said = ref(null);
const shown = ref("overview");
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const dayOf = (value) => {
  const at = new Date(value);
  const day = typeof value === "number" ? `${at.getFullYear()}-${String(at.getMonth() + 1).padStart(2, "0")}-${String(at.getDate()).padStart(2, "0")}` : String(value);
  return `${shortMonth(day)} ${day.slice(8)}`;
};
const share = (value) => `${Math.round(value)}%`;
const listMoney = (value) => money(value, said.value.currency, 0);
const paidMoney = (value) => money(value, said.value.invoiced_in || said.value.currency, 0);
const USE = computed(() => ({ memory: { label: __("Memory"), color: hue(0) }, disk: { label: __("Disk"), color: hue(4) } }));
const ROOM = computed(() => ({ workspaces: { label: __("Workspaces"), color: hue(0) }, room: { label: __("Room Left"), color: tokens.value.axisLabel } }));
const SIGNUPS = computed(() => ({ started: { label: __("Started"), color: hue(1) }, paid: { label: __("Paid"), color: hue(0) } }));

const load = async () => (said.value = await get("onedesk.one_admin.console.overview"));
load();
const stops = ["Tenant", "Offering", "Workspace Server", "Credit Reservation", "Account Request", "Workspace Error", "Health Check"].map((doctype) => followList(doctype, load));
onBeforeUnmount(() => stops.forEach((stop) => stop()));

const growth = computed(() => said.value.months.map((month, at) => ({ month, workspaces: said.value.joined[at] })));
const calls = computed(() => said.value.months.map((month, at) => ({ month, calls: said.value.calls[at] })));
const used = computed(() => said.value.months.map((month, at) => ({ month, credits: said.value.credits[at] })));
const room = computed(() => said.value.servers.map((one) => ({ server: one.server, workspaces: one.workspaces || 0, room: Math.max((one.capacity || 0) - (one.workspaces || 0), 0) })));
const checked = computed(() => said.value.health.filter((one) => one.state !== "Not Set Up"));
const failing = computed(() => said.value.health.filter((one) => one.state === "Failing").length);
const thisMonth = computed(() => said.value.invoiced.find((one) => one.month === said.value.months.at(-1))?.amount || 0);
const views = computed(() => [
  { key: "overview", label: __("Overview") },
  { key: "needs", label: __("Needs You"), count: said.value.needs.length },
]);
const RED = "var(--ink-red-7)";
const cards = computed(() => [
  { key: "live", route: "/desk/tenant?status=Live", props: { title: __("Live Workspaces"), value: said.value.live, format: count, sparkline: { data: said.value.joined, type: "area", color: hue(0) } } },
  { key: "revenue", route: "/desk/oneadmin-billing", props: { title: __("Monthly Revenue"), value: said.value.revenue, format: listMoney } },
  {
    key: "paid",
    route: "/desk/oneadmin-billing",
    props: { title: __("Paid This Month"), value: thisMonth.value, format: paidMoney, sparkline: said.value.invoiced.length > 1 ? { data: said.value.invoiced.map((one) => one.amount), type: "bar", color: hue(0) } : undefined },
  },
  {
    key: "signups",
    route: "/desk/account-request",
    props: { title: __("Signups, Last 30 Days"), value: said.value.signups_now, format: count, sparkline: said.value.signups.length > 1 ? { data: said.value.signups.map((one) => one.started), type: "bar", color: hue(1) } : undefined },
  },
  { key: "credits", route: "/desk/credit-ledger-entry", props: { title: __("Credits This Month"), value: said.value.credits.at(-1), format: count, sparkline: { data: said.value.credits, type: "bar", color: hue(4) } } },
  { key: "cost", route: "/desk/workspace-server", props: { title: __("Server Cost a Month"), value: said.value.cost, format: (value) => `$${count(value)}` } },
  { key: "errors", route: "/desk/workspace-error?status=Open", props: { title: __("Open Errors"), value: said.value.open_errors, format: count, color: said.value.open_errors ? RED : undefined } },
  {
    key: "health",
    route: "/desk/oneadmin-status",
    props: { title: __("Services Working"), value: __("{0} of {1}", [count(checked.value.length - failing.value), count(checked.value.length)]), color: failing.value ? RED : undefined },
  },
]);
const short = (release) => (release || "").slice(0, 7);
const releases = computed(() => said.value.rollout.releases.filter((one) => one.workspaces).map((one) => ({ release: short(one.release), workspaces: one.workspaces })));
const rollout = computed(() => {
  const total = said.value.rollout.total;
  const latest = said.value.rollout.releases.filter((one) => one.current).reduce((sum, one) => sum + one.workspaces, 0);
  const waiting = said.value.rollout.waiting;
  return [
    { title: __("On Latest Release"), value: total ? `${Math.round((100 * latest) / total)}%` : "–", bar: total ? Math.round((100 * latest) / total) : null },
    { title: __("Moving Now"), value: count(waiting.moving || 0) },
    { title: __("Waiting for Terms"), value: count(waiting.terms || 0) },
    { title: __("Waiting for a Window"), value: count(waiting.window || 0) },
  ];
});
const needs = computed(() =>
  said.value.needs.map((one, at) => ({
    key: at,
    label: one.title,
    below: one.detail || one.why,
    badge: one.badge ? { label: one.badge, theme: "amber" } : null,
    onClick: () => (one.doctype ? goTo("Form", one.doctype, one.name) : null),
    actions: one.action ? [{ label: one.action.label, onClick: () => call(one.action.method, one.action.args).then(load) }] : [],
  })),
);
</script>
