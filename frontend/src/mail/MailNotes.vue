<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-ink-gray-8">{{ __("Notes for the Team") }}</span>
      <span v-if="notes.length" class="text-sm text-ink-gray-5">{{ notes.length }}</span>
    </div>
    <p v-if="!notes.length" class="text-sm text-ink-gray-5">{{ __("Never sent to anybody outside.") }}</p>
    <div v-for="one in notes" :key="one.name" class="text-sm">
      <span class="font-medium text-ink-gray-8">{{ one.by }}</span>
      <span class="ms-1.5 text-ink-gray-5">{{ ago(one.creation) }}</span>
      <div class="text-ink-gray-8" v-html="one.content" />
    </div>
    <div class="flex items-center gap-1.5">
      <TextInput v-model="typed" class="flex-1" size="sm" :placeholder="__('Add a note')" @keydown.enter.prevent="save" />
      <Button size="sm" variant="subtle" icon="lucide-send-horizontal" :aria-label="__('Add Note')" :title="__('Add Note')" :disabled="!typed.trim()" @click="save" />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Button, TextInput } from "frappe-ui";

import { __, ago, call, escape } from "../kit";

const props = defineProps({
  account: { type: String, required: true },
  thread: { type: String, required: true },
  notes: { type: Array, default: () => [] },
});
const emit = defineEmits(["state"]);
const typed = ref("");

async function save() {
  if (!typed.value.trim()) return;
  emit("state", await call("onedesk.one_mail.team.note", { account: props.account, thread: props.thread, content: escape(typed.value.trim()) }));
  typed.value = "";
}
</script>
