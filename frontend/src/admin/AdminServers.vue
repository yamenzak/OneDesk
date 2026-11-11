<template>
  <Page wide>
    <Loading v-if="!servers" />
    <div v-else ref="root" class="pb-4">
      <p v-if="!servers.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No servers yet") }}</p>
      <div v-else class="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ServerCard v-for="one in servers" :key="one.server" :server="one" :tick="tick" :requests="requests[one.server] ?? null" :hue="hue" />
      </div>

      <Section v-if="traffic" :title="__('Traffic')" icon="lucide-globe" :aside="__('Last 24 Hours')" data-cards>
        <div class="grid gap-3 lg:grid-cols-3">
          <ChartCard v-if="workspaces.length" class="h-96">
            <BarChart :title="__('Requests by Workspace')" :data="workspaces" x="workspace" y="requests" split-by="workspace" stacked horizontal :x-axis="wrapped" :y-axis="{ format: count }" />
          </ChartCard>
          <ChartCard v-if="workers.length" class="h-96" :class="{ 'lg:col-span-2': workspaces.length && !buckets.length }">
            <AreaChart :title="__('Worker Requests by Hour')" :data="workers" x="hour" y="requests" split-by="script" stacked :y-axis="{ format: count }" />
          </ChartCard>
          <ChartCard v-if="buckets.length" class="h-96">
            <BarChart :title="__('R2 Storage by Bucket')" :data="buckets" x="bucket" y="size" split-by="bucket" stacked horizontal :x-axis="wrapped" :y-axis="{ format: fileSize }" />
          </ChartCard>
        </div>
        <p v-for="gap in gaps" :key="gap" class="mt-2 text-sm text-ink-gray-5">{{ gap }}</p>
      </Section>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { AreaChart, BarChart, ChartCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, Section, __, count, fileSize, followList, get, wrapped } from "../kit";
import ServerCard from "./ServerCard.vue";

const LIVE_EVERY = 30000;
const TOP = 12;

const servers = ref(null);
const traffic = ref(null);
const tick = ref(0);
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];

const load = async () => (servers.value = await get("onedesk.one_admin.metrics.cards"));
const loadTraffic = async () => (traffic.value = await get("onedesk.one_admin.metrics.traffic").catch(() => null));
load();
loadTraffic();

const stops = ["Workspace Server", "Tenant"].map((doctype) => followList(doctype, load));
const timer = setInterval(() => {
  if (document.visibilityState === "visible" && root.value?.offsetParent !== null) tick.value += 1;
}, LIVE_EVERY);
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearInterval(timer);
});

const part = (key) => traffic.value?.[key]?.data || [];
const workspaces = computed(() => part("workspaces").slice(0, TOP));
const workers = computed(() => part("workers"));
const buckets = computed(() => part("r2"));
const requests = computed(() => {
  const totals = {};
  for (const one of part("workspaces")) totals[one.server] = (totals[one.server] || 0) + one.requests;
  return totals;
});
const NAMES = () => ({ workspaces: __("requests per workspace"), workers: __("Workers"), r2: __("R2") });
const gaps = computed(() =>
  Object.entries(NAMES()).flatMap(([key, name]) => {
    const state = traffic.value?.[key]?.state;
    if (state === "refused") return [__("The Cloudflare token needs {0} to show {1}.", [traffic.value.needs[key], name])];
    return state === "unreachable" ? [__("Cloudflare did not answer for {0}.", [name])] : [];
  })
);
</script>
