<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="m-1.5 mb-0 flex h-9 shrink-0 items-center gap-3 rounded-full bg-surface-gray-3 px-3.5 text-sm font-medium text-ink-gray-7">
      <span class="flex w-8 shrink-0 justify-center">
        <Checkbox
          :modelValue="every"
          :indeterminate="!every && picked.size > 0"
          :disabled="!items.length"
          :aria-label="every ? __('Clear selection') : __('Select all')"
          :title="every ? __('Clear selection') : __('Select all')"
          @update:modelValue="(on) => emit('all', on)"
        />
      </span>
      <template v-if="picked.size">
        <span class="min-w-0 flex-1 truncate text-ink-gray-9">{{ __("{0} selected", [picked.size]) }}</span>
        <span class="flex shrink-0 items-center gap-0.5"><slot name="action" /></span>
      </template>
      <template v-else-if="wide">
        <span class="w-4 shrink-0" />
        <span class="w-52 shrink-0">{{ __("From") }}</span>
        <span class="min-w-0 flex-1">{{ __("Subject") }}</span>
        <span class="w-16 shrink-0 text-end">{{ __("Date") }}</span>
      </template>
      <span v-else class="min-w-0 flex-1 truncate">{{ __("Conversations") }}</span>
    </div>
    <div ref="scroller" class="min-h-0 flex-1 overflow-auto px-1.5" role="listbox" aria-multiselectable="true" :aria-label="__('Conversations')">
      <div v-if="!items.length" class="py-16 text-center text-base text-ink-gray-5">{{ searching ? __("No results") : __("No conversations") }}</div>
      <div
        v-for="item in items"
        :key="item.thread"
        role="option"
        :aria-selected="picked.has(item.thread)"
        class="group flex cursor-pointer gap-3 border-b border-outline-gray-1 px-3.5 [content-visibility:auto] last:border-b-0"
        :style="{ containIntrinsicSize: wide ? 'auto 44px' : 'auto 88px' }"
        :class="picked.has(item.thread) ? 'bg-surface-gray-4' : item.thread === open ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
        @click="clicked(item, $event)"
        @contextmenu="emit('menu', item.thread)"
      >
        <button
          type="button"
          role="checkbox"
          class="size-8 shrink-0 self-start rounded-full [perspective:400px]"
          :class="wide ? 'my-1.5' : 'mt-3'"
          :aria-checked="picked.has(item.thread)"
          :aria-label="__('Select')"
          :title="__('Select')"
          @click.stop="emit('toggle', item.thread, $event.shiftKey)"
        >
          <span
            class="relative block size-8 transition-transform duration-300 [transform-style:preserve-3d]"
            :class="picked.has(item.thread) ? '[transform:rotateY(-180deg)]' : ''"
          >
            <MailFace :name="item.sender_name" :email="item.sender" :picture="item.face" class="absolute inset-0 [backface-visibility:hidden]" />
            <span
              class="absolute inset-0 flex items-center justify-center rounded-full bg-surface-gray-10 text-ink-base [backface-visibility:hidden] [transform:rotateY(180deg)]"
            >
              <span class="lucide-check size-4" aria-hidden="true" />
            </span>
          </span>
        </button>
        <span v-if="wide" class="flex min-w-0 flex-1 items-center gap-3">
          <button
            type="button"
            class="shrink-0"
            :class="item.flagged ? 'text-ink-amber-6' : 'text-ink-gray-4 hover:text-ink-gray-6'"
            :title="item.flagged ? __('Unstar') : __('Star')"
            :aria-label="item.flagged ? __('Unstar') : __('Star')"
            @click.stop="emit('star', item)"
          >
            <span class="lucide-star size-4" aria-hidden="true" />
          </button>
          <span class="flex w-52 shrink-0 items-center gap-1.5">
            <span v-if="item.unread" class="size-2 shrink-0 rounded-full bg-surface-blue-6" />
            <span v-if="item.draft" class="shrink-0 text-ink-red-4">{{ __("Draft") }}</span>
            <span class="min-w-0 truncate" :class="item.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'">{{ who(item) }}</span>
            <span v-if="item.count > 1" class="shrink-0 text-sm text-ink-gray-5">{{ count(item.count) }}</span>
          </span>
          <span class="min-w-0 flex-1 truncate">
            <span :class="item.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'">{{ item.subject || __("(no subject)") }}</span>
            <span v-if="item.snippet" class="text-ink-gray-5"> – {{ item.snippet }}</span>
          </span>
          <span v-if="item.attachments" class="lucide-paperclip size-3.5 shrink-0 text-ink-gray-5" />
          <span v-if="item.done" class="lucide-circle-check size-3.5 shrink-0 text-ink-green-3" :title="__('Done')" />
          <span v-if="(item.assigned || []).length" class="lucide-user-check size-3.5 shrink-0 text-ink-gray-5" :title="__('Assigned')" />
          <span v-if="item.snoozed_until" class="lucide-alarm-clock size-3.5 shrink-0 text-ink-gray-5" :title="__('Snoozed')" />
          <span class="w-16 shrink-0 text-end text-sm" :class="item.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-5'">{{ when(item.date) }}</span>
        </span>
        <span v-else class="flex min-w-0 flex-1 flex-col gap-0.5 py-3">
          <span class="flex items-center gap-1.5">
            <span v-if="item.unread" class="size-2 shrink-0 rounded-full bg-surface-blue-6" />
            <span v-if="item.draft" class="shrink-0 text-ink-red-4">{{ __("Draft") }}</span>
            <span class="min-w-0 flex-1 truncate" :class="item.unread ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'">{{ who(item) }}</span>
            <span v-if="item.count > 1" class="text-sm text-ink-gray-5">{{ count(item.count) }}</span>
            <span v-if="item.attachments" class="lucide-paperclip size-3.5 text-ink-gray-5" />
            <span v-if="item.done" class="lucide-circle-check size-3.5 text-ink-green-3" :title="__('Done')" />
            <span v-if="(item.assigned || []).length" class="lucide-user-check size-3.5 text-ink-gray-5" :title="__('Assigned')" />
            <span v-if="item.snoozed_until" class="lucide-alarm-clock size-3.5 text-ink-gray-5" :title="__('Snoozed')" />
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
      <div v-if="more" ref="end" class="flex justify-center p-3"><LoadingIndicator class="size-4 text-ink-gray-5" /></div>
    </div>
  </div>
</template>

<script setup>
// One line per conversation: who, when, what it is about and how it starts.
// Its picture is a card: a click turns it over, right to left, to a tick on
// the colour frappe-ui's checkbox is ticked in. While any is ticked a click on
// a row ticks rather than opens, as Ctrl and Shift do. What is ticked is what
// the command row acts on. The next page comes as the list's end scrolls
// near, and rows off screen are left undrawn by the browser
// (content-visibility), so a long folder stays light.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Checkbox, LoadingIndicator } from "frappe-ui";

import { __, count } from "../kit";
import { when, who } from "./mail";
import MailFace from "./MailFace.vue";

const props = defineProps({
  items: { type: Array, default: () => [] },
  picked: { type: Set, required: true },
  open: { type: String, default: null },
  more: Boolean,
  searching: Boolean,
  wide: Boolean,
});
const emit = defineEmits(["open", "toggle", "all", "star", "more", "menu"]);

const every = computed(() => props.items.length > 0 && props.items.every((one) => props.picked.has(one.thread)));

const scroller = ref(null);
const end = ref(null);
let watching = null;
watch(
  [end, () => props.items.length],
  ([spot]) => {
    if (watching) watching.disconnect();
    if (!spot) return;
    watching = new IntersectionObserver((seen) => seen.some((one) => one.isIntersecting) && emit("more"), {
      root: scroller.value,
      rootMargin: "400px 0px",
    });
    watching.observe(spot);
  },
  { flush: "post" }
);
onBeforeUnmount(() => watching && watching.disconnect());

function clicked(item, event) {
  if (event.shiftKey || event.metaKey || event.ctrlKey || props.picked.size) return emit("toggle", item.thread, event.shiftKey);
  emit("open", item.thread);
}
</script>
