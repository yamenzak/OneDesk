<template>
  <section class="mt-8">
    <h2 class="mb-2 flex items-baseline gap-2 text-base font-medium text-ink-gray-9">
      {{ title }}<span v-if="aside" class="text-sm font-normal text-ink-gray-5">{{ aside }}</span>
    </h2>
    <slot />
  </section>
</template>

<script setup>
defineProps({ title: { type: String, required: true }, aside: { type: String, default: "" } });
</script>
