<template>
  <div ref="root" class="flex flex-col gap-3" data-cards>
    <TabButtons v-model="shown" :options="windows" class="self-end" />
    <Loading v-if="!said" />
    <template v-else>
      <div class="grid gap-3 lg:grid-cols-2">
        <ChartCard class="h-72">
          <LineChart :title="__('Time to Answer')" :data="answered" x="at" :y="['took']" :y-axis="{ min: 0, format: ms }" :series-config="{ took: { label: __('Time to Answer'), color: hue(0) } }" />
        </ChartCard>
        <ChartCard class="h-72">
          <BarChart :title="__('Checks')" :data="checked" x="at" :y="['working', 'failing']" stacked :y-axis="{ format: count }" :series-config="CHECKS" />
        </ChartCard>
      </div>
      <div class="grid gap-6 lg:grid-cols-2">
        <Section :title="__('Last Checks')" bare>
          <Rows :rows="checks" :empty="__('No checks yet')" />
        </Section>
        <Section v-if="said.incidents.length" :title="__('What Failed')" :aside="said.incidents.length" bare>
          <Rows :rows="incidents" />
        </Section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { TabButtons } from "frappe-ui";
import { BarChart, ChartCard, LineChart, useChartTokens } from "frappe-ui/charts";

import { Loading, Rows, Section, __, colors, count, dateTime, get, goTo } from "../kit";

const props = defineProps({ service: { type: String, required: true } });

const windows = [
  { label: __("24 Hours"), value: "24h" },
  { label: __("7 Days"), value: "7d" },
  { label: __("30 Days"), value: "30d" },
];
const shown = ref("24h");
const said = ref(null);
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];

const load = async () => {
  said.value = null;
  said.value = await get("onedesk.one_admin.health.history", { service: props.service, window: shown.value });
};
watch([() => props.service, shown], load, { immediate: true });

const ms = (value) => __("{0} ms", [count(value)]);
const stamped = (rows) => rows.map((one) => ({ ...one, at: new Date(one.at.replace(" ", "T")).toISOString() }));
const answered = computed(() => stamped(said.value.buckets.filter((one) => one.took !== null)));
const checked = computed(() => stamped(said.value.buckets).map((one) => ({ at: one.at, working: one.checks - one.failed, failing: one.failed })));
const CHECKS = computed(() => ({
  working: { label: __("Working"), color: hue(0) },
  failing: { label: __("Failing"), color: colors(root.value, "--ink-red-5")[0] || hue(6) },
}));

const incidents = computed(() =>
  said.value.incidents.map((one, at) => ({
    key: at,
    label: dateTime(one.started),
    below: one.detail,
    value: __("{0} checks in a row", [count(one.checks)]),
    under: __("Until {0}", [dateTime(one.ended)]),
  })),
);
const THEMES = { Working: "green", Failing: "red", "Not Set Up": "gray" };
const checks = computed(() =>
  said.value.checks.map((one) => ({
    key: one.name,
    label: dateTime(one.checked_at),
    below: one.detail,
    badge: { label: __(one.state), theme: THEMES[one.state] },
    value: one.took === null ? "" : ms(one.took),
    onClick: () => goTo("Form", "Health Check", one.name),
  })),
);
</script>
