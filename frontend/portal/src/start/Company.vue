<template>
  <div class="flex flex-col gap-4">
    <FormControl v-model="first.name" size="lg" :label="__('Company Name')" autocomplete="organization" required :description="address" :error="taken" />
    <FormControl v-model="first.country" type="combobox" size="lg" :label="__('Country')" :options="countries" :placeholder="__('Choose a country')" required />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { FormControl, debounce } from "frappe-ui";

import { __ } from "../words";
import { answers, free, held, offer } from "./wizard";

const first = computed(() => answers.companies[0]);
const countries = computed(() => offer.value.countries.map(({ label, value }) => ({ label, value })));
const address = ref("");
const taken = ref("");

const check = debounce(async (name) => {
  address.value = taken.value = "";
  if (!name.trim()) return;
  const said = await free(name).catch(() => null);
  if (!said || name !== first.value.name) return;
  if (said.free || said.slug === held.slug) address.value = __("Your address: {0}", [`${said.slug}.${offer.value.domain}`]);
  else taken.value = said.why;
}, 300);

watch(() => first.value.name, check);

onMounted(() => {
  if (first.value.name) check(first.value.name);
  if (first.value.country) return;
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  first.value.country = offer.value.countries.find((one) => one.zones.includes(zone))?.value || "";
});

const ready = computed(() => Boolean(first.value.name.trim() && first.value.country && !taken.value));

defineExpose({ ready, said: () => ({ answers: { companies: answers.companies } }) });
</script>
