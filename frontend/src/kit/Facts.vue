<template>
  <!-- What a record is, label against value: a value may open a route, run
       `onClick`, show `avatars` (the kit's People, as a record's head shows
       them) or a `tone`. -->
  <dl class="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-3.5 text-base">
    <template v-for="one in facts" :key="one.label">
      <dt class="text-ink-gray-5">{{ one.label }}</dt>
      <!-- Avatars aren't truncated: clipping the line would crop their rings. -->
      <dd class="min-w-0" :class="[one.avatars ? '' : 'truncate', one.tone === 'red' ? 'text-ink-red-5' : one.tone === 'gray' ? 'text-ink-gray-5' : 'text-ink-gray-8']">
        <button v-if="one.avatars" class="flex items-center rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="one.value" @click="one.onClick ? one.onClick() : go(one.route)">
          <People :users="one.avatars.map((person) => person.label)" :people="Object.fromEntries(one.avatars.map((person) => [person.label, { name: person.label, image: person.image }]))" :max="6" />
        </button>
        <button v-else-if="one.route || one.onClick" class="hover:underline" @click="one.onClick ? one.onClick() : go(one.route)">{{ one.value }}</button>
        <span v-else>{{ one.value }}</span>
      </dd>
    </template>
  </dl>
</template>

<script setup>
import { go } from "./desk";
import People from "./People.vue";

defineProps({ facts: { type: Array, required: true } });
</script>
