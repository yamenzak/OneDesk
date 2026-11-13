<template>
  <RadioGroup v-model="held.region" padded :description="about">
    <Radio v-for="one in offer.regions" :key="one.value" :value="one.value" :label="one.label" />
  </RadioGroup>
</template>

<script setup>
import { computed } from "vue";
import { Radio, RadioGroup } from "frappe-ui";

import { __ } from "../words";
import { held, offer } from "./wizard";

const about = __("The European Union keeps the workspace's files in the EU. This cannot be changed later.");
const ready = computed(() => offer.value.regions.some((one) => one.value === held.region));

defineExpose({ ready, said: () => ({ region: held.region }) });
</script>
