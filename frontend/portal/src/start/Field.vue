<template>
  <RadioGroup :model-value="answers.field" padded @update:model-value="choose">
    <Radio v-for="one in offer.fields" :key="one.id" :value="one.id" :label="one.label" :description="one.line" />
  </RadioGroup>
</template>

<script setup>
import { computed } from "vue";
import { Radio, RadioGroup } from "frappe-ui";

import { answers, offer } from "./wizard";

function choose(id) {
  answers.field = id;
  const preset = offer.value.fields.find((one) => one.id === id)?.apps || [];
  answers.apps = Object.fromEntries(offer.value.apps.filter((one) => !one.always).map((one) => [one.id, preset.includes(one.id)]));
}

const ready = computed(() => Boolean(answers.field));

defineExpose({ ready, said: () => ({ answers: { field: answers.field, apps: answers.apps } }) });
</script>
