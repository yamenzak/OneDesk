<template>
  <svg v-if="found" class="inline-block shrink-0" :viewBox="found.viewBox" aria-hidden="true" v-html="found.html" />
</template>

<script setup>
import { computed } from "vue";
import { symbol } from "./desk";

const props = defineProps({ name: { type: String, required: true } });
const found = computed(() => symbol(props.name));
</script>
