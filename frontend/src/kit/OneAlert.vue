<template>
  <div class="one-alert" :class="colour">
    <span class="one-alert-icon" v-html="icon" />
    <div class="one-alert-text"><slot>{{ text }}</slot></div>
    <div v-if="$slots.verbs" class="one-notice-verbs"><slot name="verbs" /></div>
  </div>
</template>

<script setup>
// The desk's alert (onedesk.alert in head.js), so a note in an island is the
// same card as one on a form: desk.css draws both.
import { computed } from "vue";

import { alertIcon } from "./desk";

const props = defineProps({ text: String, colour: { type: String, default: "blue" } });

const icon = computed(() => alertIcon(props.colour));
</script>
