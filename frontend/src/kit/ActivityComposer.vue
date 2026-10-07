<template>
  <!-- What a record's activity is written with, at its top, as a form's
       Activity has it: frappe's own comment composer, with @-mentions, sent
       through the form's add_comment, drawn as frappe ships it, and beside
       the page's filters New Email, which opens frappe's Email dialog on the
       record (onedesk.record.email).
       `reply(email, all)` opens that dialog on an email of the timeline, as
       its Reply and Reply All do on a form. -->
  <div class="flex flex-col gap-3">
    <CommentComposer
      ref="commentRef"
      :mentions="mentions"
      :placeholder="__('Write a comment')"
      :submit-label="__('Comment')"
      :submitting="sending"
      @submit="sendComment"
    />
    <div class="flex items-center gap-2">
      <slot />
      <Button v-if="canEmail" class="ms-auto" icon-left="lucide-plus" :label="__('New Email')" @click="write" />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Button } from "frappe-ui";
import { CommentComposer } from "@framework/ui/Composer";

import { __, can, comment, emailOn, mentionable } from "./desk";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
});
const emit = defineEmits(["sent"]);

const mentions = mentionable();
const canEmail = can("email", props.doctype);
const sending = ref(false);
const commentRef = ref(null);

async function sendComment({ body }) {
  sending.value = true;
  try {
    await comment(props.doctype, props.name, body);
    commentRef.value?.reset();
    emit("sent");
  } finally {
    sending.value = false;
  }
}

const sent = () => emit("sent");

/** frappe's Email dialog for a new email on the record. */
const write = () => emailOn(props.doctype, props.name, { sent });

/** frappe's Email dialog answering `email`, a timeline email; `all` copies
 * everyone it went to, as Reply All does. */
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
