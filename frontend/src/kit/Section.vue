<template>
  <!-- A titled part of a screen, on the page, divided from the next by a rule,
       or in a card of its own (`boxed`), as frappe-ui's ChartCard draws one.
       It may open where the whole of it is (`action`), as a figure does. -->
  <section :class="boxed ? 'my-5 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4' : 'border-b border-outline-gray-1 py-5 last:border-0'">
    <div class="mb-3 flex items-center justify-between gap-2">
      <h2 class="text-lg font-semibold text-ink-gray-9">{{ title }}</h2>
      <div class="flex items-center gap-1">
        <span v-if="aside !== undefined && aside !== null && aside !== ''" class="text-base text-ink-gray-5">{{ aside }}</span>
        <Button v-if="action" variant="ghost" :icon="action.icon" :aria-label="action.label" @click="action.onClick" />
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup>
import { Button } from "frappe-ui";

defineProps({ title: { type: String, required: true }, aside: [String, Number], action: Object, boxed: Boolean });
</script>
