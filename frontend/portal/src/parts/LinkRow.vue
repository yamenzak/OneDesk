<template>
  <component :is="to ? RouterLink : 'div'" :to="to || undefined" :class="['block border-b border-outline-gray-1 px-4 py-3 last:border-b-0', to && 'hover:bg-surface-gray-1']">
    <span class="flex items-center justify-between gap-2">
      <span class="min-w-0 truncate text-sm font-medium text-ink-gray-8">{{ name }}</span>
      <Badge v-if="status" class="shrink-0" :theme="tone" :label="status" />
    </span>
    <span class="mt-0.5 block truncate text-sm tabular-nums text-ink-gray-5">{{ line }}</span>
  </component>
</template>

<script setup>
import { RouterLink } from "vue-router";
import { Badge } from "frappe-ui";

defineProps({
  to: { type: String, default: "" },
  name: { type: String, required: true },
  line: { type: String, default: "" },
  status: { type: String, default: "" },
  tone: { type: String, default: "gray" },
});
</script>
