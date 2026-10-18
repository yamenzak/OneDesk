<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-3">
      <Avatar size="md" :label="writer.name" :image="writer.image" />
      <div class="min-w-0 flex-1 rounded-5 border border-outline-gray-2">
        <CommentComposer
          ref="commentRef"
          :mentions="mentions"
          :placeholder="__('Write a comment')"
          :submit-label="__('Comment')"
          :submitting="sending"
          @submit="sendComment"
        />
      </div>
    </div>
    <div class="flex items-center gap-2">
      <slot />
      <Button v-if="canEmail" class="ms-auto" icon-left="lucide-plus" :label="__('New Email')" @click="write" />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Avatar, Button } from "frappe-ui";
import { CommentComposer } from "@framework/ui/Composer";

import { __, can, comment, emailOn, me, mentionable, userInfo } from "./desk";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
  vet: Function,
});
const emit = defineEmits(["sent"]);

const mentions = mentionable();
const writer = userInfo(me());
const canEmail = can("email", props.doctype);
const sending = ref(false);
const commentRef = ref(null);

async function sendComment({ body }) {
  sending.value = true;
  try {
    await props.vet?.(body);
    await comment(props.doctype, props.name, body);
    commentRef.value?.reset();
    emit("sent");
  } finally {
    sending.value = false;
  }
}

const sent = () => emit("sent");

const write = () => emailOn(props.doctype, props.name, { sent });

const reply = (email, all = false) => {
  const data = email.data || {};
  const last = {
    name: data.name,
    sender: data.sender,
    recipients: data.to || "",
    cc: data.cc || "",
    bcc: data.bcc || "",
    subject: data.subject,
    content: data.content,
    communication_date: email.timestamp,
  };
  return emailOn(props.doctype, props.name, { email: last, all, sent });
};

defineExpose({ reply, write });
</script>
