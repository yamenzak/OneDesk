<template>
  <div class="flex flex-col gap-8">
    <div v-for="(one, at) in more" :key="at" class="flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <p class="text-base font-medium text-ink-gray-8">{{ __("Company {0}", [at + 2]) }}</p>
        <Button variant="ghost" icon="lucide-x" :aria-label="__('Remove')" @click="remove(at)" />
      </div>
      <FormControl v-model="one.name" size="lg" :label="__('Company Name')" required />
      <FormControl v-model="one.country" type="combobox" size="lg" :label="__('Country')" :options="countries" required />
    </div>
    <Button class="self-start" variant="subtle" icon-left="lucide-plus" :label="__('Add Company')" @click="add" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Button, FormControl } from "frappe-ui";

import { __ } from "../words";
import { answers, offer } from "./wizard";

const more = computed(() => answers.companies.slice(1));
const countries = computed(() => offer.value.countries.map(({ label, value }) => ({ label, value })));

const add = () => answers.companies.push({ name: "", country: answers.companies[0].country });
const remove = (at) => answers.companies.splice(at + 1, 1);

const ready = computed(() => more.value.every((one) => one.name.trim() && one.country));

defineExpose({ ready, said: () => ({ answers: { companies: answers.companies } }) });
</script>
