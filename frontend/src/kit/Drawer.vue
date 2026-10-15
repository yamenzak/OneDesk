<template>
  <!-- A record opened beside the page, as monday and Asana open an item:
       the page stays where it was. Escape or the cross closes it. -->
  <Teleport to="body" :disabled="true">
    <Transition enter-from-class="translate-x-full" leave-to-class="translate-x-full" enter-active-class="transition-transform duration-200" leave-active-class="transition-transform duration-150">
      <aside v-if="open" class="fixed inset-y-0 end-0 z-40 flex w-full max-w-xl flex-col border-s border-outline-gray-2 bg-surface-elevation-1" role="dialog" :aria-label="title" @keydown.esc="$emit('close')">
        <header class="flex items-center gap-2 border-b border-outline-gray-1 px-5 py-3">
          <slot name="head" />
          <div class="ms-auto flex items-center gap-1">
            <slot name="actions" />
            <Button variant="ghost" icon="lucide-x" :aria-label="__('Close')" @click="$emit('close')" />
          </div>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto"><slot /></div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { Button } from "frappe-ui";

defineProps({ open: Boolean, title: String });
defineEmits(["close"]);
</script>
