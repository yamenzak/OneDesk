<template>
  <section :class="boxed ? 'my-5 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4' : bare ? 'py-5' : 'py-5'">
    <div class="mb-3 flex items-center justify-between gap-2">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span v-if="icon" :class="icon" class="size-4 shrink-0 text-ink-gray-5" aria-hidden="true" /><span><Branded :text="title" :marked="marked" /></span>
      </h2>
      <div class="flex items-center gap-1">
        <span v-if="aside !== undefined && aside !== null && aside !== ''" class="text-base text-ink-gray-5">{{ aside }}</span>
        <template v-for="one in [action].flat().filter(Boolean)" :key="one.label">
          <Button v-if="one.text" variant="ghost" :icon-left="one.icon" :label="one.label" @click="one.onClick" />
          <Button v-else variant="ghost" :icon="one.icon" :aria-label="one.label" @click="one.onClick" />
        </template>
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup>
import { Button } from "frappe-ui";
import Branded from "./Branded.vue";

defineProps({ title: { type: String, required: true }, aside: [String, Number], action: [Object, Array], boxed: Boolean, icon: String, bare: Boolean, marked: Boolean });
</script>
