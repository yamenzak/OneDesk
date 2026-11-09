<template>
  <div ref="root" class="text-ink-gray-8">
    <div class="mb-3 flex justify-end">
      <TabButtons v-model="shown" :options="windows" />
    </div>
    <Loading v-if="!said" />
    <template v-else>
      <p v-for="gap in gaps" :key="gap" class="mb-2 text-sm text-ink-gray-5">{{ gap }}</p>
      <div class="grid gap-3 lg:grid-cols-2">
        <ChartCard v-if="cpu.length" class="h-72">
          <AreaChart :title="__('CPU')" :data="cpu" x="at" :y="Object.keys(CPU)" stacked :y-axis="{ min: 0, max: 100, format: share }" :series-config="CPU" />
        </ChartCard>
        <ChartCard v-if="burst.length" class="h-72">
          <AreaChart :title="__('CPU Burst Left')" :data="burst" x="at" :y="['burst']" :y-axis="{ min: 0, max: 100, format: share }" :series-config="{ burst: { label: __('CPU Burst'), color: hue(3) } }" />
        </ChartCard>
        <ChartCard v-if="system.length" class="h-72">
          <AreaChart :title="__('Memory')" :data="system" x="at" :y="Object.keys(MEMORY)" stacked :y-axis="{ format: fileSize }" :series-config="MEMORY" />
        </ChartCard>
        <ChartCard v-if="system.length" class="h-72">
          <LineChart :title="__('Disk Used')" :data="system" x="at" :y="['disk']" :y-axis="{ min: 0, max: 100, format: share }" :series-config="{ disk: { label: __('Disk'), color: hue(4) } }" />
        </ChartCard>
        <ChartCard v-if="io.length" class="h-72">
          <LineChart :title="__('Disk Read and Write')" :data="io" x="at" :y="['read', 'write']" :y-axis="{ format: rate }" :series-config="IO" />
        </ChartCard>
        <ChartCard v-if="system.length" class="h-72">
          <LineChart :title="__('Network')" :data="system" x="at" :y="['received', 'sent']" :y-axis="{ format: rate }" :series-config="NETWORK" />
        </ChartCard>
        <ChartCard v-if="system.length" class="h-72">
          <LineChart :title="__('Load')" :data="system" x="at" :y="['load1', 'load5', 'load15']" :y-axis="{ format: quantity }" :series-config="LOAD" />
        </ChartCard>
        <ChartCard v-if="database.length" class="h-72">
          <AreaChart :title="__('Database Queries')" :data="database" x="at" :y="Object.keys(QUERIES)" stacked :y-axis="{ format: count }" :series-config="QUERIES" />
        </ChartCard>
        <ChartCard v-if="database.length" class="h-72">
          <LineChart :title="__('Database Connections')" :data="database" x="at" :y="['connected', 'allowed']" :y-axis="{ format: count }" :series-config="CONNECTIONS" />
        </ChartCard>
      </div>
      <p v-if="!cpu.length && !system.length && !database.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No readings from this server") }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { TabButtons } from "frappe-ui";
import { AreaChart, ChartCard, LineChart, useChartTokens } from "frappe-ui/charts";

import { Loading, __, count, fileSize, get, quantity } from "../kit";

const LIVE_EVERY = 30000;

const props = defineProps({ server: { type: String, required: true } });

const windows = [
  { label: __("1 Hour"), value: "1h" },
  { label: __("6 Hours"), value: "6h" },
  { label: __("24 Hours"), value: "24h" },
  { label: __("7 Days"), value: "1w" },
];
const shown = ref("1h");
const said = ref(null);
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];

const load = async () => {
  said.value = await get("onedesk.one_admin.metrics.charts", { server: props.server, window: shown.value }).catch(() => null);
};
watch([() => props.server, shown], load, { immediate: true });
const timer = setInterval(() => {
  if (document.visibilityState === "visible" && root.value?.offsetParent !== null) load();
}, LIVE_EVERY);
onBeforeUnmount(() => clearInterval(timer));

const share = (value) => `${Math.round(value)}%`;
const rate = (value) => `${fileSize(value)}/s`;
const stamped = (rows) => (rows || []).map((one) => ({ ...one, at: new Date(one.time).toISOString() }));

const system = computed(() => stamped(said.value?.system));
const lightsail = computed(() => stamped(said.value?.lightsail));
const database = computed(() => stamped(said.value?.database));
const cpu = computed(() => (system.value.length ? system.value : lightsail.value.filter((one) => one.cpu !== undefined).map((one) => ({ ...one, user: one.cpu }))));
const burst = computed(() => lightsail.value.filter((one) => one.burst !== undefined));
const io = computed(() => (lightsail.value.some((one) => one.read !== undefined) ? lightsail.value : system.value));

const gaps = computed(() => {
  const states = said.value?.states || {};
  const out = [];
  if (states.pilot !== "ok") out.push(__("Pilot did not answer for this server."));
  if (said.value?.provider === "AWS" && states.lightsail === "refused") out.push(__("The AWS key needs lightsail:GetInstanceMetricData to show CPU burst."));
  return out;
});

const CPU = computed(() => ({
  user: { label: __("User"), color: hue(0) },
  system: { label: __("System"), color: hue(2) },
  iowait: { label: __("Waiting for Disk"), color: hue(4) },
  other: { label: __("Other"), color: tokens.value.axisLabel },
}));
const MEMORY = computed(() => ({
  used: { label: __("Used"), color: hue(0) },
  cached: { label: __("Cached"), color: hue(3) },
  swap: { label: __("Swap"), color: hue(8) },
}));
const IO = computed(() => ({ read: { label: __("Read"), color: hue(0) }, write: { label: __("Write"), color: hue(4) } }));
const NETWORK = computed(() => ({ received: { label: __("Received"), color: hue(0) }, sent: { label: __("Sent"), color: hue(4) } }));
const LOAD = computed(() => ({
  load1: { label: __("1 Minute"), color: hue(0) },
  load5: { label: __("5 Minutes"), color: hue(3) },
  load15: { label: __("15 Minutes"), color: hue(6) },
}));
const QUERIES = computed(() => ({
  select: { label: __("Select"), color: hue(0) },
  insert: { label: __("Insert"), color: hue(2) },
  update: { label: __("Update"), color: hue(4) },
  delete: { label: __("Delete"), color: hue(8) },
  other: { label: __("Other"), color: tokens.value.axisLabel },
}));
const CONNECTIONS = computed(() => ({ connected: { label: __("Connected"), color: hue(0) }, allowed: { label: __("Allowed"), color: tokens.value.axisLabel } }));
</script>
