<template>
  <!-- A titled part of a screen, on the page, divided from the next by a rule. -->
  <section class="border-b border-outline-gray-1 py-5 last:border-0">
    <div class="mb-3 flex items-baseline justify-between gap-2">
      <h2 class="text-lg font-semibold text-ink-gray-9">{{ title }}</h2>
      <span v-if="aside !== undefined && aside !== null && aside !== ''" class="text-base text-ink-gray-5">{{ aside }}</span>
    </div>
    <slot />
  </section>
</template>

<script setup>
defineProps({ title: { type: String, required: true }, aside: [String, Number] });
</script>
