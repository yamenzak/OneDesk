<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-2.5">
      <button
        type="button"
        role="checkbox"
        class="flex size-8 shrink-0 items-center justify-center"
        :aria-checked="every ? 'true' : picked.size ? 'mixed' : 'false'"
        :aria-label="every ? __('Clear selection') : __('Select all')"
        :title="every ? __('Clear selection') : __('Select all')"
        :disabled="!items.length"
        @click="emit('all', !every)"
      >
        <span class="flex size-4 items-center justify-center rounded-1 border" :class="picked.size ? 'border-outline-gray-5 bg-surface-gray-7 text-ink-white' : 'border-outline-gray-3 bg-surface-white'">
          <span v-if="picked.size" :class="every ? 'lucide-check' : 'lucide-minus'" class="size-3" aria-hidden="true" />
        </span>
      </button>
      <span class="min-w-0 flex-1 truncate font-semibold text-ink-gray-9">{{ title }}</span>
      <span v-if="picked.size" class="shrink-0 text-sm text-ink-gray-5">{{ __("{0} selected", [picked.size]) }}</span>
    </div>
    <div class="min-h-0 flex-1 overflow-auto" role="listbox" aria-multiselectable="true" :aria-label="__('Conversations')">
      <div v-if="!items.length" class="py-16 text-center text-base text-ink-gray-5">{{ searching ? __("No results") : __("No conversations") }}</div>
      <div
        v-for="item in items"
        :key="item.thread"
        role="option"
        :aria-selected="picked.has(item.thread)"
        class="group flex cursor-pointer gap-3 border-b border-outline-gray-1 px-4 py-3"
        :class="picked.has(item.thread) ? 'bg-surface-blue-2' : item.thread === open ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
        @click="clicked(item, $event)"
        @contextmenu="emit('menu', item.thread)"
      >
        <button
          type="button"
          role="checkbox"
          class="relative size-8 shrink-0"
          :aria-checked="picked.has(item.thread)"
          :aria-label="__('Select')"
          @click.stop="emit('toggle', item.thread, $event.shiftKey)"
        >
          <MailFace :name="item.sender_name" :email="item.sender" :picture="item.face" :class="picked.size ? 'invisible' : 'group-hover:invisible'" />
          <span class="absolute inset-0 items-center justify-center" :class="picked.size ? 'flex' : 'hidden group-hover:flex'">
            <span
              class="flex size-4 items-center justify-center rounded-1 border"
              :class="picked.has(item.thread) ? 'border-outline-gray-5 bg-surface-gray-7 text-ink-white' : 'border-outline-gray-3 bg-surface-white'"
            >
              <span v-if="picked.has(item.thread)" class="lucide-check size-3" aria-hidden="true" />
            </span>
          </span>
        </button>
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
// Its picture turns into a box to tick when pointed at, and every picture
// does while any is ticked; a click then ticks rather than opens, as Ctrl and
// Shift do. What is ticked is what the command row acts on.
import { computed } from "vue";
import { Button } from "frappe-ui";

import { __, count } from "../kit";
import { when, who } from "./mail";
import MailFace from "./MailFace.vue";

const props = defineProps({
  title: String,
  items: { type: Array, default: () => [] },
  picked: { type: Set, required: true },
  open: { type: String, default: null },
  more: Boolean,
  searching: Boolean,
});
const emit = defineEmits(["open", "toggle", "all", "star", "more", "menu"]);

const every = computed(() => props.items.length > 0 && props.items.every((one) => props.picked.has(one.thread)));

function clicked(item, event) {
  if (event.shiftKey || event.metaKey || event.ctrlKey || props.picked.size) return emit("toggle", item.thread, event.shiftKey);
  emit("open", item.thread);
}
</script>
