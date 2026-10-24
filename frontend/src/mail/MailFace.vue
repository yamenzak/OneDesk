<template>
  <img v-if="picture" :src="picture" alt="" loading="lazy" class="size-8 shrink-0 rounded-full object-cover" />
  <span v-else class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-medium" :class="tone" aria-hidden="true">{{ initials }}</span>
</template>

<script setup>
// A sender's picture, or their initials on a colour that is always theirs.
import { computed } from "vue";

const props = defineProps({ name: String, email: String, picture: String });

const TONES = [
  "bg-surface-blue-2 text-ink-blue-7",
  "bg-surface-green-2 text-ink-green-7",
  "bg-surface-amber-2 text-ink-amber-7",
  "bg-surface-red-2 text-ink-red-7",
  "bg-surface-violet-2 text-ink-violet-7",
  "bg-surface-cyan-2 text-ink-cyan-7",
  "bg-surface-pink-2 text-ink-pink-7",
  "bg-surface-teal-2 text-ink-teal-7",
  "bg-surface-orange-2 text-ink-orange-7",
  "bg-surface-purple-2 text-ink-purple-7",
];

const initials = computed(() => {
  const text = (props.name || props.email || "?").trim();
  const parts = text.replace(/[<>"']/g, "").split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0] || "?")[0] + ((parts[1] || "")[0] || "")).toUpperCase();
});

const tone = computed(() => {
  let hash = 0;
  for (const char of props.email || props.name || "?") hash = (hash * 31 + char.charCodeAt(0)) % 9973;
  return TONES[hash % TONES.length];
});
</script>
