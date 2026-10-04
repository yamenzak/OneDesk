<template>
  <!-- The tasks by status, as one bar, each status its share and colour, and
       a key under it. A status opens the project's tasks. -->
  <div>
    <div class="flex h-2.5 gap-0.5 overflow-hidden rounded-full">
      <span v-for="one in parts" :key="one.status" class="h-full first:rounded-s-full last:rounded-e-full" :class="SURFACE[TASK_STATUS[one.status]] || SURFACE.gray" :style="{ width: `${one.share}%` }" :title="`${__(one.status)} · ${one.n}`" />
    </div>
    <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2">
      <button v-for="one in parts" :key="one.status" class="flex items-center gap-1.5 text-base text-ink-gray-7 hover:text-ink-gray-9" @click="$emit('open', one.status)">
        <span class="size-2 rounded-full" :class="SURFACE[TASK_STATUS[one.status]] || SURFACE.gray" />
        {{ __(one.status) }}
        <span class="tabular-nums text-ink-gray-5">{{ one.n }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { __ } from "../kit";
import { SURFACE, TASK_STATUS } from "./colors";

const props = defineProps({ statuses: { type: Object, required: true } });
defineEmits(["open"]);
const ORDER = ["Completed", "Pending Review", "Working", "Open", "Overdue"];
const parts = computed(() => {
  const all = Object.values(props.statuses).reduce((a, b) => a + b, 0) || 1;
  return Object.entries(props.statuses)
    .map(([status, n]) => ({ status, n, share: (100 * n) / all }))
    .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
});
</script>
