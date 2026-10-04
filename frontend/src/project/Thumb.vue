<template>
  <!-- A featured photo or video, small and cropped. -->
  <img v-if="item.kind === 'photo'" :src="item.thumbnail || item.url" :alt="item.title" class="size-full object-cover" loading="lazy" />
  <span v-else class="relative block size-full bg-surface-gray-7">
    <video :src="`${item.url}#t=0.1`" muted preload="metadata" class="size-full object-cover" />
    <span class="lucide-play absolute inset-0 m-auto size-5 text-white" />
  </span>
</template>

<script setup>
defineProps({ item: { type: Object, required: true } });
</script>
