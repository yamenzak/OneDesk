<template>
  <!-- A comment box over what happened on the record, newest first: frappe's own timeline. -->
  <div class="flex flex-col gap-4 pb-10 pt-2">
    <div class="flex items-end gap-2">
      <Textarea v-model="text" class="flex-1" :rows="2" :placeholder="__('Write a comment')" @keydown.meta.enter="send" @keydown.ctrl.enter="send" />
      <Button variant="solid" :label="__('Comment')" :disabled="!text.trim()" :loading="sending" @click="send" />
    </div>
    <TimelineContainer>
      <ActivityTimeline :activities="activities" :loading="loading" />
    </TimelineContainer>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Button, Textarea } from "frappe-ui";
import { ActivityTimeline, TimelineContainer, useActivityTimeline } from "@framework/ui/ActivityTimeline";

import { __, comment } from "../kit";

const props = defineProps({ doctype: { type: String, required: true }, name: { type: String, required: true } });
const { activities, loading, reload } = useActivityTimeline(props.doctype, props.name);
const text = ref("");
const sending = ref(false);

async function send() {
  const said = text.value.trim();
  if (!said || sending.value) return;
  sending.value = true;
  try {
    const escaped = said.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
    await comment(props.doctype, props.name, `<div>${escaped}</div>`);
    text.value = "";
    reload?.();
  } finally {
    sending.value = false;
  }
}
</script>
