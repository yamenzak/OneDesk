<template>
  <div v-if="said.notes.length || said.actions.length" class="flex flex-col gap-2">
    <OneAlert v-for="(one, i) in said.notes" :key="`note-${i}`" :text="one.text" :colour="TONES.includes(one.tone) ? one.tone : 'gray'" />
    <div v-if="said.actions.length" class="flex flex-wrap gap-2">
      <Button v-for="(one, i) in said.actions" :key="`action-${i}`" size="sm" variant="subtle" :label="one.label" @click="one.handler()" />
    </div>
  </div>
</template>

<script setup>
import { Button } from "frappe-ui";

import OneAlert from "./OneAlert.vue";

defineProps({ said: { type: Object, required: true } });

const TONES = ["gray", "blue", "green", "orange", "red"];
</script>
