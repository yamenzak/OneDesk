<template>
  <section :class="boxed ? 'my-5 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4' : 'border-b border-outline-gray-1 py-5 last:border-0 [&:has(+[data-cards])]:border-b-0'">
    <div class="mb-3 flex items-center justify-between gap-2">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span v-if="icon" :class="icon" class="size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />{{ title }}
      </h2>
      <div class="flex items-center gap-1">
        <span v-if="aside !== undefined && aside !== null && aside !== ''" class="text-base text-ink-gray-5">{{ aside }}</span>
        <Button v-if="action && action.text" variant="ghost" :icon-left="action.icon" :label="action.label" @click="action.onClick" />
        <Button v-else-if="action" variant="ghost" :icon="action.icon" :aria-label="action.label" @click="action.onClick" />
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup>
import { Button } from "frappe-ui";

defineProps({ title: { type: String, required: true }, aside: [String, Number], action: Object, boxed: Boolean, icon: String });
</script>
