<template>
  <!-- An item's picture, or a tile with its icon where it has none. -->
  <img v-if="image" :src="image" alt="" class="size-10 shrink-0 rounded-3 border border-outline-gray-1 object-cover" loading="lazy" />
  <span v-else class="grid size-10 shrink-0 place-items-center rounded-3 bg-surface-gray-2 text-ink-gray-5">
    <span :class="`lucide-${icon} size-4`" aria-hidden="true" />
  </span>
</template>

<script setup>
defineProps({ image: { type: String, default: "" }, icon: { type: String, default: "package" } });
</script>
