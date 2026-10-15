<template>
  <!-- A record's facts, a label over each value, in a row that wraps. -->
  <dl class="flex flex-wrap gap-x-10 gap-y-4">
    <div v-for="one in facts" :key="one.label" class="min-w-0">
      <dt class="mb-1 text-sm text-ink-gray-5">{{ one.label }}</dt>
      <dd :class="['text-base text-ink-gray-8', one.lines && 'whitespace-pre-line']">
        <RouterLink v-if="one.to" :to="one.to" class="underline decoration-outline-gray-3 underline-offset-2 hover:text-ink-gray-9">{{ one.value }}</RouterLink>
        <template v-else>{{ one.value }}</template>
      </dd>
    </div>
  </dl>
</template>

<script setup>
defineProps({ facts: { type: Array, default: () => [] } });
</script>
