<template>
  <!-- What a record is, label against value: a value may open a route, run
       `onClick`, show `avatars` (frappe-ui's Avatar) or a `tone`. -->
  <dl class="grid grid-cols-[7rem_minmax(0,1fr)] gap-y-2.5 text-base">
    <template v-for="one in facts" :key="one.label">
      <dt class="text-ink-gray-5">{{ one.label }}</dt>
      <dd class="min-w-0 truncate" :class="one.tone === 'red' ? 'text-ink-red-5' : one.tone === 'gray' ? 'text-ink-gray-5' : 'text-ink-gray-8'">
        <button v-if="one.avatars" class="flex items-center -space-x-1" :aria-label="one.value" @click="one.onClick ? one.onClick() : go(one.route)">
          <Avatar v-for="person in one.avatars.slice(0, 6)" :key="person.label" :label="person.label" :image="person.image" size="sm" class="ring-2 ring-surface-base" />
          <span v-if="one.avatars.length > 6" class="ps-2 text-ink-gray-5">+{{ one.avatars.length - 6 }}</span>
        </button>
        <button v-else-if="one.route || one.onClick" class="hover:underline" @click="one.onClick ? one.onClick() : go(one.route)">{{ one.value }}</button>
        <span v-else>{{ one.value }}</span>
      </dd>
    </template>
  </dl>
</template>

<script setup>
import { Avatar } from "frappe-ui";

import { go } from "./desk";

defineProps({ facts: { type: Array, required: true } });
</script>
