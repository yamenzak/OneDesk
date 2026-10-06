<template>
  <!-- A row of figures: frappe-ui's NumberCard, borderless, as Frappe Books'
       dashboard, or each in a card of its own (`boxed`), as frappe-ui's
       ChartCard draws one.
       A figure may open its documents (`route`), carry an `action`, or ask
       for the next step with a `button` under it. -->
  <div class="grid grid-cols-2" :class="[COLUMNS[figures.length] || 'lg:grid-cols-4', boxed ? 'gap-3' : 'gap-x-8 gap-y-6 pb-3']">
    <div v-for="one in figures" :key="one.title" class="flex min-w-0 flex-col" :class="{ [CARD]: boxed }">
      <NumberCard :title="one.title" :value="one.value" :card="false" :color="one.alarm ? 'var(--ink-red-5)' : undefined">
        <template v-if="one.action" #actions>
          <Button variant="ghost" :icon="one.action.icon" :aria-label="one.action.label" @click="one.action.onClick" />
        </template>
        <template v-else-if="one.route" #actions>
          <Button variant="ghost" icon="lucide-arrow-up-right" :aria-label="one.title" @click="go(one.route)" />
        </template>
      </NumberCard>
      <div v-if="one.note" class="mt-1 line-clamp-3 whitespace-pre-line text-sm text-ink-gray-5">{{ one.note }}</div>
      <Button v-if="one.button" class="mt-2 self-start" size="sm" :icon-left="one.button.icon" :label="one.button.label" @click="one.button.onClick" />
      <Progress v-if="one.bar !== undefined && one.bar !== null" :value="one.bar" size="md" class="mt-3" />
    </div>
  </div>
</template>

<script setup>
import { Button, Progress } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";

import { go } from "./desk";

defineProps({ figures: { type: Array, required: true }, boxed: Boolean });
// frappe-ui's ChartCard surface.
const CARD = "rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3";
const COLUMNS = { 3: "lg:grid-cols-3", 5: "lg:grid-cols-5" };
</script>
