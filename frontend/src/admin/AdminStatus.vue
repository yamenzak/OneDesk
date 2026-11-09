<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else>
      <OneAlert v-if="failing.length" colour="red" class="mt-6">{{ failingSaid }}</OneAlert>
      <OneAlert v-else colour="green" class="mt-6">{{ __("All Services Working") }}</OneAlert>
      <Section :title="__('Services')" icon="lucide-heart-pulse">
        <Rows :rows="services" />
      </Section>
      <Section :title="__('Last 30 Days')" icon="lucide-calendar-days" data-cards>
        <ChartCard class="h-96">
          <HeatmapChart :title="__('Share of Checks Failed')" :data="said.days" x="day" y="service" value="share" :min="0" :max="100" :format="share" :x-axis="{ format: dayOf }" :y-axis="{ format: nameOf }" />
        </ChartCard>
      </Section>
      <Section v-if="said.incidents.length" :title="__('What Failed')" icon="lucide-triangle-alert">
        <Rows :rows="incidents" />
      </Section>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { ChartCard, HeatmapChart } from "frappe-ui/charts";

import { Loading, OneAlert, Page, Rows, Section, __, clock, count, date, followList, get, shortMonth } from "../kit";

const FAILING = "Failing";
const THEMES = { Working: "green", Failing: "red", "Not Set Up": "gray" };
const said = ref(null);

const load = async () => (said.value = await get("onedesk.one_admin.health.board"));
load();
onBeforeUnmount(followList("Health Check", load));

const failing = computed(() => said.value.services.filter((one) => one.state === FAILING));
const failingSaid = computed(() =>
  failing.value.length === 1 ? __("{0} is failing", [__(failing.value[0].service)]) : __("{0} services are failing", [count(failing.value.length)])
);
const share = (value) => `${Math.round(value)}%`;
const nameOf = (value) => __(value);
const dayOf = (value) => `${shortMonth(String(value))} ${String(value).slice(8)}`;
const checked = (one) => (one.checked_at ? __("Checked {0}", [`${date(one.checked_at)} ${clock(one.checked_at)}`]) : __("Not checked yet"));
const route = (one) => `/desk/health-check?service=${encodeURIComponent(one.service)}`;

const services = computed(() =>
  said.value.services.map((one) => ({
    key: one.service,
    label: __(one.service),
    dot: THEMES[one.state],
    below: one.state === FAILING && one.detail ? `${one.detail} · ${checked(one)}` : checked(one),
    badge: { label: __(one.state), theme: THEMES[one.state] },
    value: one.uptime === null ? "—" : `${one.uptime}%`,
    under: one.took ? `${count(one.took)} ms` : "",
    route: route(one),
  }))
);
const incidents = computed(() =>
  said.value.incidents.map((one, at) => ({
    key: at,
    label: __(one.service),
    below: one.detail,
    value: `${date(one.started)} ${clock(one.started)}`,
    under: __("{0} checks in a row", [count(one.checks)]),
    route: route(one),
  }))
);
</script>
