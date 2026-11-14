<template>
  <RadioGroup :model-value="answers.field" padded @update:model-value="chooseField">
    <Radio v-for="one in offer.fields" :key="one.id" :value="one.id" :label="one.label" :description="one.line" />
  </RadioGroup>
</template>

<script setup>
import { computed } from "vue";
import { Radio, RadioGroup } from "frappe-ui";

import { answers, chooseField, offer } from "./wizard";

const ready = computed(() => Boolean(answers.field));

defineExpose({ ready, said: () => ({ answers: { field: answers.field, apps: answers.apps } }) });
</script>
