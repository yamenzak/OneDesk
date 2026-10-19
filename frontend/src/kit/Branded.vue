<template>
  <template v-for="(part, i) in parts" :key="i">
    <span v-if="part.one" class="one-name one-solo inline-flex items-baseline gap-1 whitespace-nowrap"><img class="one-mark inline-block size-[1.05em] self-center" :src="MARK" alt="" />{{ NAME }}</span>
    <template v-else>{{ part }}</template>
  </template>
</template>

<script setup>
import { computed } from "vue";
import { onedesk } from "./desk";

const props = defineProps({ text: { type: [String, Number], default: "" } });
const MARK = "/assets/onedesk/images/one.svg";
const NAME = "One";
const parts = computed(() => {
  const text = props.text === null || props.text === undefined ? "" : String(props.text);
  const brand = onedesk()?.brand;
  return brand?.parts ? brand.parts(text) : [text];
});
</script>
