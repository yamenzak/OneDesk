<template>
  <Dropdown v-if="!readonly" :options="choices">
    <template #trigger>
      <button class="inline-flex rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="label ? `${label}, ${shown}` : shown">
        <Badge :label="shown" :theme="theme(value)" :variant="variant" size="md" />
      </button>
    </template>
  </Dropdown>
  <Badge v-else :label="shown" :theme="theme(value)" :variant="variant" size="md" />
</template>

<script setup>
import { computed } from "vue";
import { Badge, Dropdown } from "frappe-ui";

import { __ } from "./desk";

const props = defineProps({
  value: String,
  options: { type: Array, required: true },
  colors: { type: Object, default: () => ({}) },
  label: String,
  empty: String,
  readonly: Boolean,
  variant: { type: String, default: "subtle" },
});
const emit = defineEmits(["change"]);

const theme = (value) => props.colors[value] || "gray";
const shown = computed(() => (props.value ? __(props.value) : props.empty || "–"));
const choices = computed(() =>
  props.options.map((one) => ({
    label: __(one),
    selected: one === props.value,
    onClick: () => one !== props.value && emit("change", one),
  }))
);
</script>
