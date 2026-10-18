<template>
  <section class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base">
    <header v-if="title || $slots.actions" class="flex min-h-11 items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-2">
      <h2 class="flex items-center gap-2 text-base font-medium text-ink-gray-9">
        <span v-if="icon" :class="[icon, 'size-4 text-ink-gray-5']" aria-hidden="true" />
        {{ title }}
        <span v-if="count" class="text-sm font-normal tabular-nums text-ink-gray-5">{{ count }}</span>
      </h2>
      <div class="flex items-center gap-2"><slot name="actions" /></div>
    </header>
    <div :class="flush ? '' : 'p-4'"><slot /></div>
    <footer v-if="$slots.foot" class="border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-3"><slot name="foot" /></footer>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: "" },
  icon: { type: String, default: "" },
  count: { type: [String, Number], default: "" },
  flush: { type: Boolean, default: false },
});
</script>
