<template>
  <!-- Milestones as a line: done ones filled, the next one ringed. -->
  <div class="flex overflow-x-auto pt-1">
    <button v-for="(one, i) in milestones" :key="one.name" class="relative flex min-w-28 flex-1 flex-col items-start gap-0.5 pt-5 text-start" @click="go(`/desk/task/${one.name}`)">
      <span class="absolute inset-x-0 top-[5px] h-0.5" :class="one.done ? 'bg-surface-gray-7' : 'bg-surface-gray-3'" />
      <span class="absolute start-0 top-0 h-3 w-3 rounded-full border-2" :class="one.done ? 'border-outline-gray-5 bg-surface-gray-7' : i === next ? 'border-outline-gray-5 bg-surface-base' : 'border-outline-gray-3 bg-surface-base'" />
      <span class="pe-3 text-base font-medium text-ink-gray-8">{{ one.subject }}</span>
      <span class="text-sm text-ink-gray-5">{{ date(one.due) }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { date, go } from "../kit";

const props = defineProps({ milestones: { type: Array, required: true } });
const next = computed(() => props.milestones.findIndex((one) => !one.done));
</script>
