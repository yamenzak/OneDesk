<template>
  <div class="flex flex-col gap-4">
    <p class="text-p-base text-ink-gray-6">{{ __("Start from one of these, and change anything.") }}</p>
    <section v-for="group in groups" :key="group.name" class="flex flex-col gap-2">
      <h3 v-if="group.name" class="text-sm font-medium text-ink-gray-5">{{ group.name }}</h3>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <button
          v-for="one in group.starters"
          :key="one.key"
          type="button"
          class="flex flex-col gap-1 rounded-3 border border-outline-gray-2 bg-surface-base p-3 text-start hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          @click="emit('pick', one)"
        >
          <span class="flex items-center gap-2 text-base font-medium text-ink-gray-9">
            <span :class="[lucide(one.icon), 'size-4 shrink-0 text-ink-gray-6']" aria-hidden="true" />
            {{ one.title }}
          </span>
          <span class="text-p-sm text-ink-gray-6">{{ one.about }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { __ } from "../kit";
import { lucide } from "./icons";

const props = defineProps({ starters: { type: Array, default: () => [] } });
const emit = defineEmits(["pick"]);

const groups = computed(() => {
  const said = [];
  for (const one of props.starters) {
    let held = said.find((group) => group.name === one.group);
    if (!held) said.push((held = { name: one.group, starters: [] }));
    held.starters.push(one);
  }
  return said;
});
</script>
