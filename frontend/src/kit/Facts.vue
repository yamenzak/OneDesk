<template>
  <!-- What a record is, label against value. -->
  <dl class="grid grid-cols-[7rem_minmax(0,1fr)] gap-y-2.5 text-base">
    <template v-for="one in facts" :key="one.label">
      <dt class="text-ink-gray-5">{{ one.label }}</dt>
      <dd class="min-w-0 truncate text-ink-gray-8">
        <button v-if="one.route" class="hover:underline" @click="go(one.route)">{{ one.value }}</button>
        <span v-else>{{ one.value }}</span>
      </dd>
    </template>
  </dl>
</template>

<script setup>
import { go } from "./desk";

defineProps({ facts: { type: Array, required: true } });
</script>
