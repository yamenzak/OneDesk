<template>
  <!-- A record's name, its badges, one line of who and when, and the people on it. -->
  <div class="flex items-end justify-between gap-4 py-6">
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <h1 class="text-2xl font-semibold text-ink-gray-9">{{ title }}</h1>
        <Badge v-for="one in badges" :key="one.label" :label="one.label" :theme="one.theme || 'gray'" size="md" />
      </div>
      <div v-if="line.length" class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-base text-ink-gray-6">
        <template v-for="(part, i) in line" :key="i">
          <span v-if="i" class="text-ink-gray-4">·</span>
          <button v-if="part.route" class="hover:text-ink-gray-9 hover:underline" @click="go(part.route)">{{ part.label }}</button>
          <span v-else>{{ part.label }}</span>
        </template>
      </div>
    </div>
    <div v-if="people.length" class="flex shrink-0 -space-x-1.5">
      <Tooltip v-for="one in people.slice(0, 5)" :key="one.user" :text="one.name">
        <Avatar :label="one.name" :image="one.image" size="md" class="ring-2 ring-surface-white" />
      </Tooltip>
    </div>
  </div>
</template>

<script setup>
import { Avatar, Badge, Tooltip } from "frappe-ui";

import { go } from "./desk";

defineProps({
  title: { type: String, required: true },
  badges: { type: Array, default: () => [] },
  line: { type: Array, default: () => [] },
  people: { type: Array, default: () => [] },
});
</script>
