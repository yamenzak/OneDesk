<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-2.5">
      <span class="min-w-0 flex-1 truncate font-semibold text-ink-gray-9">{{ title }}</span>
      <span v-if="picked.size" class="text-sm text-ink-gray-5">{{ __("{0} selected", [picked.size]) }}</span>
    </div>
    <div class="min-h-0 flex-1 overflow-auto" role="listbox" aria-multiselectable="true" :aria-label="__('Conversations')">
      <div v-if="!items.length" class="py-16 text-center text-base text-ink-gray-5">{{ searching ? __("No results") : __("No conversations") }}</div>
      <div
        v-for="item in items"
        :key="item.thread"
        role="option"
        :aria-selected="picked.has(item.thread)"
        class="group flex cursor-pointer gap-3 border-b border-outline-gray-1 px-4 py-3"
        :class="item.thread === open ? 'bg-surface-gray-2' : picked.has(item.thread) ? 'bg-surface-blue-1' : 'hover:bg-surface-gray-1'"
        @click="clicked(item, $event)"
      >
        <span class="relative">
          <MailFace :name="item.sender_name" :email="item.sender" :picture="item.face" />
          <input
            type="checkbox"
            class="absolute -start-1 -top-1 size-4 opacity-0 group-hover:opacity-100"
            :class="{ 'opacity-100': picked.has(item.thread) }"
            :checked="picked.has(item.thread)"
            :aria-label="__('Select')"
            @click.stop="emit('toggle', item.thread, $event.shiftKey)"
          />
        </span>
        <span class="flex min-w-0 flex-1 flex-col gap-0.5">
          <span class="flex items-center gap-1.5">
            <span v-if="item.unread" class="size-2 shrink-0 rounded-full bg-surface-blue-6" />
            <span class="min-w-0 flex-1 truncate" :class="item.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'">{{ who(item) }}</span>
            <span v-if="item.count > 1" class="text-sm text-ink-gray-5">{{ count(item.count) }}</span>
            <span v-if="item.attachments" class="lucide-paperclip size-3.5 text-ink-gray-5" />
            <span class="shrink-0 text-sm text-ink-gray-5">{{ when(item.date) }}</span>
          </span>
          <span class="flex items-center gap-1">
            <span class="min-w-0 flex-1 truncate text-sm" :class="item.unread ? 'font-medium text-ink-gray-9' : 'text-ink-gray-8'">{{ item.subject || __("(no subject)") }}</span>
            <button
              type="button"
              class="shrink-0"
              :class="item.flagged ? 'text-ink-amber-6' : 'text-ink-gray-4 opacity-0 group-hover:opacity-100'"
              :title="item.flagged ? __('Unstar') : __('Star')"
              @click.stop="emit('star', item)"
            >
              <span class="lucide-star size-4" aria-hidden="true" />
            </button>
          </span>
          <span class="line-clamp-2 text-sm text-ink-gray-5">{{ item.snippet }}</span>
        </span>
      </div>
      <div v-if="more" class="p-3"><Button variant="subtle" :label="__('Load More')" @click="emit('more')" /></div>
    </div>
  </div>
</template>

<script setup>
// One line per conversation: who, when, what it is about and how it starts.
import { Button } from "frappe-ui";

import { __, count } from "../kit";
import { when, who } from "./mail";
import MailFace from "./MailFace.vue";

defineProps({
  title: String,
  items: { type: Array, default: () => [] },
  picked: { type: Set, required: true },
  open: { type: String, default: null },
  more: Boolean,
  searching: Boolean,
});
const emit = defineEmits(["open", "toggle", "star", "more"]);

function clicked(item, event) {
  if (event.shiftKey || event.metaKey || event.ctrlKey) return emit("toggle", item.thread, event.shiftKey);
  emit("open", item.thread);
}
</script>
