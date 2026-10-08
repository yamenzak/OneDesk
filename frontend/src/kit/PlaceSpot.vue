<template>
  <!-- What the workspace's extensions add to a place on the page
       (one_studio/places.py): their notes as frappe-ui's Alert, in the tone
       they asked for, then their buttons. -->
  <div v-if="said.notes.length || said.actions.length" class="flex flex-col gap-2">
    <Alert v-for="(one, i) in said.notes" :key="`note-${i}`" :title="one.text" :theme="TONES[one.tone] || 'gray'" />
    <div v-if="said.actions.length" class="flex flex-wrap gap-2">
      <Button v-for="(one, i) in said.actions" :key="`action-${i}`" size="sm" variant="subtle" :label="one.label" @click="one.handler()" />
    </div>
  </div>
</template>

<script setup>
import { Alert, Button } from "frappe-ui";

defineProps({ said: { type: Object, required: true } });

// places.js names its tones as desk does; frappe-ui calls orange amber.
const TONES = { gray: "gray", blue: "blue", green: "green", orange: "amber", red: "red" };
</script>
