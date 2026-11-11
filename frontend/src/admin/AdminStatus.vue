<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else ref="root" class="pb-4">
      <OneAlert v-if="failing.length" colour="red" class="mt-6">{{ failingSaid }}</OneAlert>
      <OneAlert v-else-if="working" colour="green" class="mt-6">{{ __("All Services Working") }}</OneAlert>

      <Figures :figures="figures" :columns="4" class="mt-6" />

      <Section :title="__('Services')" icon="lucide-heart-pulse" :aside="count(said.services.length)">
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <ServiceCard v-for="one in said.services" :key="one.service" :service="one" :hue="hue" :chosen="one.service === shownService" @open="pick(one.service)" />
        </div>
      </Section>

      <div ref="history">
        <Section :title="__(shownService)" icon="lucide-history" :action="{ text: true, label: __('All Checks'), onClick: () => go(route(shownService)) }">
          <ServiceHistory :service="shownService" />
        </Section>
      </div>

      <Section v-if="said.days.length" :title="__('Last 30 Days')" icon="lucide-calendar-days" data-cards>
        <ChartCard class="h-96">
          <HeatmapChart :title="__('Share of Checks Failed')" :data="said.days" x="day" y="service" value="share" :min="0" :max="100" :format="share" :x-axis="{ format: dayOf }" :y-axis="{ format: nameOf }" />
        </ChartCard>
      </Section>

      <Section v-if="said.incidents.length" :title="__('What Failed')" icon="lucide-triangle-alert" :aside="said.incidents.length">
        <Rows :rows="incidents" />
      </Section>

    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { ChartCard, HeatmapChart, useChartTokens } from "frappe-ui/charts";

import { Figures, Loading, OneAlert, Page, Rows, Section, __, count, dateTime, followList, get, go, shortMonth } from "../kit";
import ServiceCard from "./ServiceCard.vue";
import ServiceHistory from "./ServiceHistory.vue";

const FAILING = "Failing";
const said = ref(null);
const picked = ref(null);
const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];

const load = async () => (said.value = await get("onedesk.one_admin.health.board"));
load();
onBeforeUnmount(followList("Health Check", load));

const checkedOnes = computed(() => said.value.services.filter((one) => one.state !== "Not Set Up"));
const failing = computed(() => said.value.services.filter((one) => one.state === FAILING));
const working = computed(() => said.value.services.every((one) => one.state === "Working"));
const shownService = computed(() => picked.value || failing.value[0]?.service || said.value.services[0].service);
const history = ref();
const pick = (service) => {
  picked.value = service;
  history.value?.scrollIntoView({ behavior: "smooth", block: "start" });
};
const failingSaid = computed(() =>
  failing.value.length === 1 ? __("{0} is failing", [__(failing.value[0].service)]) : __("{0} services are failing", [count(failing.value.length)]),
);
const share = (value) => `${Math.round(value)}%`;
const nameOf = (value) => __(value);
const dayOf = (value) => `${shortMonth(String(value))} ${String(value).slice(8)}`;
const route = (service) => `/desk/health-check?service=${encodeURIComponent(service)}`;

const answered = computed(() => checkedOnes.value.filter((one) => one.took !== null));
const figures = computed(() => [
  { title: __("Services Working"), value: __("{0} of {1}", [count(checkedOnes.value.length - failing.value.length), count(checkedOnes.value.length)]), alarm: Boolean(failing.value.length) },
  { title: __("Uptime, 30 Days"), value: said.value.uptime === null ? "–" : `${said.value.uptime}%` },
  { title: __("Average Time to Answer"), value: answered.value.length ? __("{0} ms", [count(answered.value.reduce((sum, one) => sum + one.took, 0) / answered.value.length)]) : "–" },
  { title: __("Times Failed, 30 Days"), value: count(said.value.incidents.length) },
]);

const incidents = computed(() =>
  said.value.incidents.map((one, at) => ({
    key: at,
    label: __(one.service),
    below: one.detail,
    value: dateTime(one.started),
    under: __("{0} checks in a row", [count(one.checks)]),
    onClick: () => pick(one.service),
  })),
);
</script>
