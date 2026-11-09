<template>
  <div class="overflow-hidden rounded-4 border border-outline-gray-1 bg-surface-elevation-2">
    <div class="grid grid-cols-[minmax(0,2fr)_6rem_6rem_5rem_5rem_6rem_6rem] gap-3 bg-surface-gray-2 px-4 py-2 text-sm font-medium text-ink-gray-7">
      <span>{{ __("Server") }}</span>
      <span>{{ __("Status") }}</span>
      <span class="text-end">{{ __("Workspaces") }}</span>
      <span class="text-end">{{ __("Memory") }}</span>
      <span class="text-end">{{ __("Disk") }}</span>
      <span>{{ __("Release") }}</span>
      <span class="text-end">{{ __("Cost") }}</span>
    </div>
    <button
      v-for="one in rows"
      :key="one.name"
      type="button"
      class="grid w-full grid-cols-[minmax(0,2fr)_6rem_6rem_5rem_5rem_6rem_6rem] items-center gap-3 border-t border-outline-gray-1 px-4 py-2.5 text-start hover:bg-surface-gray-1"
      @click="goTo('Form', 'Workspace Server', one.name)"
    >
      <span class="min-w-0">
        <span class="block truncate text-base font-medium text-ink-gray-9">{{ one.server }}</span>
        <span class="block truncate text-sm text-ink-gray-5">{{ [one.provider, one.region].filter(Boolean).join(" · ") }}</span>
      </span>
      <span><Badge :label="__(one.status)" :theme="THEMES[one.status] || 'gray'" /></span>
      <span class="text-end text-base tabular-nums text-ink-gray-8">
        {{ one.capacity ? __("{0} of {1}", [one.workspaces, one.capacity]) : one.workspaces }}
      </span>
      <span class="text-end text-base tabular-nums text-ink-gray-8">{{ share(one.memory) }}</span>
      <span class="text-end text-base tabular-nums text-ink-gray-8">{{ share(one.disk) }}</span>
      <span class="truncate text-sm text-ink-gray-5">{{ one.release || "\u2014" }}</span>
      <span class="text-end text-base tabular-nums text-ink-gray-8">{{ one.cost ? `$${one.cost}` : "\u2014" }}</span>
    </button>
  </div>
</template>

<script setup>
import { Badge } from "frappe-ui";

import { __, goTo } from "../kit";

defineProps({ rows: { type: Array, required: true } });
const THEMES = { Up: "green", "Filling Up": "amber", Full: "amber", Down: "red" };
const share = (value) => (value ? `${Math.round(value)}%` : "\u2014");
</script>
