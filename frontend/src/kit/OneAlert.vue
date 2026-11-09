<template>
  <div class="flex items-center gap-2 rounded-4 bg-surface-gray-1 px-4 py-2 text-base text-ink-gray-8">
    <span class="flex size-7 shrink-0 items-center justify-center self-start rounded-full text-ink-white" :class="BACKGROUNDS[colour] || BACKGROUNDS.blue">
      <span :class="icon" class="size-4" aria-hidden="true" />
    </span>
    <div class="min-w-0 flex-1"><slot>{{ text }}</slot></div>
    <div v-if="$slots.verbs" class="flex flex-wrap gap-1"><slot name="verbs" /></div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const ICONS = {
  red: "lucide-circle-alert",
  orange: "lucide-triangle-alert",
  yellow: "lucide-triangle-alert",
  green: "lucide-circle-check",
  gray: "lucide-info",
  blue: "lucide-info",
};

const BACKGROUNDS = {
  red: "bg-surface-red-5",
  orange: "bg-surface-amber-5",
  yellow: "bg-surface-amber-5",
  green: "bg-surface-green-5",
  gray: "bg-surface-gray-5",
  blue: "bg-surface-blue-5",
};

const props = defineProps({ text: String, colour: { type: String, default: "blue" } });

const icon = computed(() => ICONS[props.colour] || ICONS.blue);
</script>
