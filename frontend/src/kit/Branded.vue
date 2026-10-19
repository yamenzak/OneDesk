<template>
  <template v-for="(part, i) in parts" :key="i">
    <span v-if="part.one" class="one-name one-solo inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="mark.viewBox" aria-hidden="true" v-html="mark.html" /><span class="font-light">{{ NAME }}</span></span>
    <template v-else>{{ part }}</template>
  </template>
</template>

<script setup>
import { computed } from "vue";
import { onedesk, symbol } from "./desk";

const props = defineProps({ text: { type: [String, Number], default: "" } });
const NAME = "One";
const mark = symbol("one");
const parts = computed(() => {
  const text = props.text === null || props.text === undefined ? "" : String(props.text);
  const brand = onedesk()?.brand;
  return brand?.parts ? brand.parts(text) : [text];
});
</script>
