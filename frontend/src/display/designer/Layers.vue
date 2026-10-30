<template>
  <div class="flex flex-col gap-0.5 px-2 pb-3">
    <p v-if="!rows.length" class="px-2 py-1 text-sm text-ink-gray-5">{{ __("Nothing on this slide yet. Add text, a picture or a shape from the bar above.") }}</p>
    <div
      v-for="one in rows"
      :key="one.id"
      class="group flex items-center gap-1.5 rounded-2 px-1.5 py-1 text-sm"
      :class="[d.s.chosen.includes(one.id) ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2', over === one.id ? 'ring-1 ring-outline-blue-5' : '']"
      :draggable="d.writable.value && renaming !== one.id"
      @click="d.choose(one.id, $event.shiftKey || $event.metaKey || $event.ctrlKey)"
      @dblclick="rename(one)"
      @dragstart="dragged = one.id"
      @dragover.prevent="over = one.id"
      @dragleave="over = null"
      @drop.prevent="dropOn(one)"
      @dragend="(dragged = null), (over = null)"
    >
      <svg v-if="marks[one.kind]" class="h-4 w-4 shrink-0 text-ink-gray-5" :viewBox="marks[one.kind].viewBox" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="marks[one.kind].html" />
      <TextInput v-if="renaming === one.id" ref="field" v-model="draft" size="sm" class="min-w-0 flex-1" @keydown.enter="done(one)" @keydown.esc="renaming = null" @blur="done(one)" @click.stop />
      <span v-else class="min-w-0 flex-1 truncate" :class="one.hidden ? 'text-ink-gray-4' : ''">{{ called(one) }}</span>
      <Button
        size="sm"
        variant="ghost"
        :class="one.hidden ? '' : 'opacity-0 group-hover:opacity-100'"
        :icon="one.hidden ? 'lucide-eye-off' : 'lucide-eye'"
        :tooltip="one.hidden ? __('Show') : __('Hide')"
        :aria-label="one.hidden ? __('Show') : __('Hide')"
        :disabled="!d.writable.value"
        @click.stop="d.set(one, 'hidden', one.hidden ? 0 : 1)"
      />
      <Button
        size="sm"
        variant="ghost"
        :class="one.locked ? '' : 'opacity-0 group-hover:opacity-100'"
        :icon="one.locked ? 'lucide-lock' : 'lucide-lock-open'"
        :tooltip="one.locked ? __('Unlock') : __('Lock')"
        :aria-label="one.locked ? __('Unlock') : __('Lock')"
        :disabled="!d.writable.value"
        @click.stop="d.set(one, 'locked', one.locked ? 0 : 1)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import { Button, TextInput } from "frappe-ui";

import { __, symbol } from "../../kit";
import { useDesigner } from "./store";

const d = useDesigner();
const dragged = ref(null);
const over = ref(null);
const renaming = ref(null);
const draft = ref("");
const field = ref(null);

// Top of the list is top of the slide: the last block drawn.
const rows = computed(() => [...d.blocks.value].reverse());
const marks = computed(() => Object.fromEntries(Object.entries(d.s.schema?.kinds || {}).map(([kind, spec]) => [kind, symbol(spec.icon)])));

function called(one) {
  if (one.name) return one.name;
  if (one.kind === "text" && one.text) return one.text.split("\n")[0].slice(0, 40);
  if (one.kind === "shape") {
    const spec = d.s.schema.properties.shape;
    return spec.labels[spec.options.indexOf(one.shape)] || d.s.schema.kinds.shape.label;
  }
  return d.s.schema.kinds[one.kind].label;
}

async function rename(one) {
  if (!d.writable.value) return;
  renaming.value = one.id;
  draft.value = one.name || called(one);
  await nextTick();
  field.value?.[0]?.el?.focus?.();
}

function done(one) {
  if (renaming.value !== one.id) return;
  renaming.value = null;
  d.set(one, "name", draft.value.trim().slice(0, 60));
}

// Dropped on a row: drawn just above it.
function dropOn(one) {
  over.value = null;
  if (!dragged.value || dragged.value === one.id) return;
  const list = d.blocks.value;
  const at = list.findIndex((b) => b.id === one.id);
  d.moveLayer(dragged.value, list[at + 1]?.id ?? null);
  dragged.value = null;
}
</script>
