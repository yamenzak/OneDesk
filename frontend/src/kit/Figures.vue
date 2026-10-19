<template>
  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2" :class="COLUMNS[columns || figures.length] || 'lg:grid-cols-4'">
    <div v-for="one in figures" :key="one.title" class="flex min-w-0 flex-col" :class="{ [CARD]: !one.sparkline }">
      <Tooltip :text="one.other ? `${one.other.label}: ${one.other.value}` : ''" :disabled="!one.other" :hover-delay="150">
      <NumberCard
        :title="one.title"
        :value="one.value"
        :card="!!one.sparkline"
        :class="{ 'flex-1': one.sparkline, [TAXED]: one.other }"
        :color="one.alarm ? 'var(--ink-red-7)' : undefined"
        :sparkline="one.sparkline"
        :delta="one.delta"
        :delta-format="one.deltaFormat"
        :delta-caption="one.sparkline ? one.note : undefined"
        :negative-is-better="one.negativeIsBetter"
      >
        <template v-if="one.action" #actions>
          <Button variant="ghost" :icon="one.action.icon" :aria-label="one.action.label" @click="one.action.onClick" />
        </template>
        <template v-else-if="one.route" #actions>
          <Button variant="ghost" icon="lucide-arrow-up-right" :aria-label="one.title" @click="go(one.route)" />
        </template>
      </NumberCard>
      </Tooltip>
      <div v-if="one.note && !one.sparkline" class="mt-1 line-clamp-3 whitespace-pre-line text-sm text-ink-gray-5">{{ one.note }}</div>
      <Button v-if="one.button" class="mt-2 self-start" size="sm" :icon-left="one.button.icon" :label="one.button.label" @click="one.button.onClick" />
      <Progress v-if="one.bar !== undefined && one.bar !== null" :value="one.bar" size="md" class="mt-3" />
    </div>
  </div>
</template>

<script setup>
import { Button, Progress, Tooltip } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";

import { go } from "./desk";

defineProps({ figures: { type: Array, required: true }, columns: Number });
const CARD = "rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3";
const TAXED = "cursor-help [&_.tabular-nums>span:first-child]:underline [&_.tabular-nums>span:first-child]:decoration-dashed [&_.tabular-nums>span:first-child]:decoration-[var(--ink-gray-4)] [&_.tabular-nums>span:first-child]:decoration-1 [&_.tabular-nums>span:first-child]:underline-offset-4";
const COLUMNS = { 2: "lg:grid-cols-2", 3: "lg:grid-cols-3", 5: "lg:grid-cols-3", 6: "lg:grid-cols-3" };
</script>
