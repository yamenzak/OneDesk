<template>
  <!-- Milestones as a line: done ones filled, the next one ringed, a late one
       red. One on a sub-project says which (milestones.where). -->
  <div class="flex overflow-x-auto pt-1">
    <button v-for="(one, i) in milestones" :key="one.name" class="relative flex min-w-32 flex-1 flex-col items-start gap-0.5 pt-5 text-start" @click="go(`/desk/task/${one.name}`)">
      <span class="absolute inset-x-0 top-[5px] h-0.5" :class="one.done ? 'bg-surface-gray-7' : 'bg-surface-gray-3'" />
      <span class="absolute start-0 top-0 h-3 w-3 rounded-full border-2" :class="ring(one, i)" />
      <span class="pe-3 text-base font-medium text-ink-gray-8">{{ one.subject }}</span>
      <span v-if="one.where" class="pe-3 text-sm text-ink-gray-5">{{ one.where }}</span>
      <span class="pe-3 text-sm tabular-nums" :class="late(one) ? 'text-ink-red-4' : 'text-ink-gray-5'">{{ when(one) }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { __, date, go } from "../kit";

const props = defineProps({ milestones: { type: Array, required: true } });
const next = computed(() => props.milestones.findIndex((one) => !one.done));

const late = (one) => !one.done && one.days !== null && one.days < 0;
const ring = (one, i) =>
  one.done ? "border-outline-gray-5 bg-surface-gray-7" : late(one) ? "border-outline-red-3 bg-surface-red-5" : i === next.value ? "border-outline-gray-5 bg-surface-base" : "border-outline-gray-3 bg-surface-base";

// The date, and for one still to do how far off or how late it is.
function when(one) {
  if (!one.due) return __("No date");
  const day = date(one.due);
  if (one.done || one.days === null) return day;
  const off = one.days === -1 ? __("1 day late") : one.days < 0 ? __("{0} days late", [-one.days]) : one.days === 0 ? __("Today") : one.days === 1 ? __("Tomorrow") : __("In {0} days", [one.days]);
  return `${day} · ${off}`;
}
</script>
