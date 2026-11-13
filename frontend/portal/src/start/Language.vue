<template>
  <div class="flex flex-col gap-4">
    <FormControl v-model="answers.language" type="select" size="lg" :label="__('Language')" :options="offer.languages" required />
    <FormControl v-model="first.currency" type="combobox" size="lg" :label="__('Currency')" :options="currencies" required />
    <FormControl v-model="answers.time_zone" type="combobox" size="lg" :label="__('Time Zone')" :options="zones" required />
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { FormControl } from "frappe-ui";

import { boot } from "../words";
import { answers, offer } from "./wizard";

const first = computed(() => answers.companies[0]);
const country = computed(() => offer.value.countries.find((one) => one.value === first.value.country) || { zones: [] });
const currencies = computed(() => [...new Set(offer.value.countries.map((one) => one.currency).filter(Boolean))].sort().map((one) => ({ label: one, value: one })));
const browser = Intl.DateTimeFormat().resolvedOptions().timeZone;
const zones = computed(() => [...new Set([...country.value.zones, browser])].map((one) => ({ label: one, value: one })));

onMounted(() => {
  if (!answers.language) answers.language = offer.value.languages.some((one) => one.value === boot().lang) ? boot().lang : "en";
  if (!first.value.currency) first.value.currency = country.value.currency || "";
  const own = country.value.zones;
  if (own.length && !own.includes(answers.time_zone)) answers.time_zone = own.includes(browser) ? browser : own[0];
  else if (!answers.time_zone) answers.time_zone = browser;
});

const ready = computed(() => Boolean(answers.language && first.value.currency && answers.time_zone));

defineExpose({ ready, said: () => ({ answers: { language: answers.language, time_zone: answers.time_zone, companies: answers.companies } }) });
</script>
