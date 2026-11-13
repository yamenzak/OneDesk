<template>
  <p v-if="!offer.plans.length" class="text-p-base text-ink-gray-6">{{ __("No plan is on offer at the moment.") }}</p>
  <RadioGroup v-else v-model="held.plan" padded>
    <Radio v-for="one in offer.plans" :key="one.name" :value="one.name" :label="`${one.label} · ${one.price}`" :description="about(one)" />
  </RadioGroup>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { Radio, RadioGroup } from "frappe-ui";

import { __ } from "../words";
import { held, offer } from "./wizard";

const about = (one) =>
  [one.trial, one.description, one.quota, one.includes.length ? __("Includes {0}.", [one.includes.join(", ")]) : ""].filter(Boolean).join(" · ");

onMounted(() => {
  if (!offer.value.plans.some((one) => one.name === held.plan)) held.plan = offer.value.plans[0]?.name || null;
});

const ready = computed(() => Boolean(held.plan));

defineExpose({ ready, said: () => ({ plan: held.plan }) });
</script>
