<template>
  <!-- Nothing to show: a quiet line in the middle of the page. -->
  <div class="flex flex-col items-center gap-1 py-16 text-center">
    <p class="text-base font-medium text-ink-gray-7">{{ title }}</p>
    <p v-if="line" class="text-p-sm text-ink-gray-5">{{ line }}</p>
  </div>
</template>

<script setup>
defineProps({ title: { type: String, required: true }, line: { type: String, default: "" } });
</script>
