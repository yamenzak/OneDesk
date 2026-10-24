<template>
  <nav class="flex flex-col gap-0.5 py-1 text-base" :aria-label="__('Mailboxes')">
    <div v-if="!boxes.length" class="px-3 py-2 text-sm text-ink-gray-5">{{ __("No mailboxes") }}</div>
    <div v-for="box in boxes" :key="box.name">
      <button
        type="button"
        class="flex w-full items-center gap-1.5 rounded-3 px-2 py-1.5 text-start text-ink-gray-8 hover:bg-surface-gray-2"
        :aria-expanded="!folded(box)"
        @click="emit('fold', box.name)"
      >
        <span :class="folded(box) ? 'lucide-chevron-right' : 'lucide-chevron-down'" class="size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span :class="box.workspace ? 'lucide-building-2' : box.shared ? 'lucide-users' : 'lucide-at-sign'" class="size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
        <span class="min-w-0 flex-1 truncate" :title="box.email">{{ called(box) }}</span>
        <span v-if="box.error" class="lucide-triangle-alert size-4 text-ink-amber-7" :title="box.error" />
        <span v-if="folded(box) && box.unread" class="text-sm text-ink-gray-6">{{ box.unread }}</span>
      </button>
      <div v-if="called(box) !== box.email" class="truncate ps-9 text-sm text-ink-gray-5">{{ box.email }}</div>
      <template v-if="!folded(box)">
        <button
          v-for="folder in box.folders"
          :key="folder.name"
          type="button"
          class="flex w-full items-center gap-2 rounded-3 py-1.5 pe-2 text-start hover:bg-surface-gray-2"
          :class="[here(box, folder) ? 'bg-surface-gray-3 font-medium text-ink-gray-9' : 'text-ink-gray-7', INDENT[Math.min(depth(folder), 4)]]"
          @click="emit('choose', box.name, folder.name)"
        >
          <span :class="kindOf(folder)[0]" class="size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
          <span class="min-w-0 flex-1 truncate" :class="{ 'font-semibold': folder.unread }">{{ folderLabel(folder) }}</span>
          <span v-if="folder.unread && folder.kind !== 'Sent' && folder.kind !== 'Trash'" class="text-sm text-ink-gray-6">{{ folder.unread }}</span>
        </button>
      </template>
    </div>
    <Button class="mt-2 justify-start" variant="ghost" icon-left="lucide-plug" :label="__('Connect Mailbox')" @click="emit('connect')" />
  </nav>
</template>

<script setup>
// The mailboxes the reader may read, each with its folders, folded as the
// reader left them; in the window's nav pane.
import { Button } from "frappe-ui";

import { __ } from "../kit";
import { called, depth, folderLabel, kindOf } from "./mail";

const props = defineProps({
  boxes: { type: Array, default: () => [] },
  box: { type: Object, default: null },
  folder: { type: Object, default: null },
  folds: { type: Object, default: () => ({}) },
  searching: Boolean,
});
const emit = defineEmits(["fold", "choose", "connect"]);

const INDENT = ["ps-8", "ps-11", "ps-14", "ps-16", "ps-20"];

function folded(box) {
  if (box.name in props.folds) return props.folds[box.name];
  return !(props.box && props.box.name === box.name);
}

const here = (box, folder) => !props.searching && props.box?.name === box.name && props.folder?.name === folder.name;
</script>
