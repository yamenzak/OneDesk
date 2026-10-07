<template>
  <!-- What a record's activity is written with, at its foot, as a form's
       timeline has a comment box and New Email: frappe's own comment composer,
       with @-mentions, and its email composer, the two switched as Frappe CRM
       switches them. Each sends as frappe does (the form's add_comment and
       communication.email.make), so what is written lands on the record's
       timeline. `reply(email)` opens the email composer on an email of the
       timeline. -->
  <div class="space-y-2">
    <TabButtons v-model="mode" :options="MODES" />
    <CommentComposer
      v-if="mode === 'comment'"
      ref="commentRef"
      :mentions="mentions"
      :placeholder="__('Write a comment')"
      :submit-label="__('Comment')"
      :submitting="sending"
      @submit="sendComment"
    />
    <EmailComposer
      v-else
      ref="emailRef"
      v-model:to="to"
      v-model:cc="cc"
      v-model:bcc="bcc"
      v-model:subject="subject"
      v-model:quoted="quoted"
      show-subject
      :search-recipients="searchRecipients"
      :upload-function="uploadFile"
      :placeholder="__('Write an email')"
      :submit-label="__('Send')"
      :submitting="sending"
      @submit="sendEmail"
    />
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";
import { FileUploadHandler, TabButtons, toast } from "frappe-ui";
import { CommentComposer, EmailComposer } from "@framework/ui/Composer";

import { __, call, comment, me, mentionable } from "./desk";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
  // The subject a new email starts with: the record's title, or its name,
  // as frappe's own email dialog starts one.
  title: { type: String, default: "" },
});
const emit = defineEmits(["sent"]);

const MODES = [
  { label: __("Comment"), value: "comment", iconLeft: "lucide-message-square" },
  { label: __("Email"), value: "email", iconLeft: "lucide-mail" },
];
const mode = ref("comment");
const sending = ref(false);
const commentRef = ref(null);
const emailRef = ref(null);

const mentions = mentionable();

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

const to = ref([]);
const cc = ref([]);
const bcc = ref([]);
const subject = ref("");
const quoted = ref("");
let inReplyTo = null;
// A new email starts with the record's title as its subject.
watch(mode, (now) => now === "email" && !subject.value && (subject.value = props.title || props.name));

// The workspace's contacts, as frappe's email dialog suggests them.
async function searchRecipients(query) {
  const found = await call("frappe.email.get_contact_list", { txt: query || "" });
  return (found || []).map((one) => ({ email: one.value, label: one.description || one.value }));
}

// An attachment, attached to the record as frappe's email dialog attaches it.
function uploadFile(file) {
  return new FileUploadHandler().upload(file, { doctype: props.doctype, docname: props.name, private: true });
}

async function sendEmail({ body, attachments }) {
  if (!to.value.length) return toast.error(__("Add who it is to"));
  sending.value = true;
  try {
    const list = (people) => people.map((one) => one.email).join(", ");
    await call("frappe.core.doctype.communication.email.make", {
      doctype: props.doctype,
      name: props.name,
      recipients: list(to.value),
      cc: list(cc.value),
      bcc: list(bcc.value),
      subject: subject.value || props.title || props.name,
      content: quoted.value ? `${body}<br><blockquote>${quoted.value}</blockquote>` : body,
      send_email: 1,
      attachments: attachments.map((one) => one.name),
      in_reply_to: inReplyTo,
    });
    emailRef.value?.reset();
    to.value = [];
    cc.value = [];
    bcc.value = [];
    subject.value = props.title || props.name;
    quoted.value = "";
    inReplyTo = null;
    toast.success(__("Email sent"));
    emit("sent");
  } finally {
    sending.value = false;
  }
}

// The addresses in a list as frappe stores one ("a@x.com, Bo <b@y.com>").
const addresses = (list) =>
  String(list || "")
    .split(/[,;\n]/)
    .map((one) => (one.match(/<([^>]+)>/)?.[1] || one).trim())
    .filter(Boolean)
    .map((email) => ({ email, label: email }));

/** Opens the email composer on `email`, a timeline email, as desk's Reply
 * does: to its sender, or to whom it went when the reader sent it, its copies
 * kept, "Re:" its subject, its words quoted. */
async function reply(email) {
  const data = email.data || {};
  const own = addresses(data.sender)[0]?.email?.toLowerCase() === me()?.toLowerCase();
  mode.value = "email";
  to.value = own ? addresses(data.to) : addresses(data.sender).map((one) => ({ ...one, label: email.author?.fullname || one.email }));
  cc.value = addresses(data.cc);
  const said = data.subject || props.title || props.name;
  subject.value = /^re:/i.test(said.trim()) ? said : __("Re: {0}", [said]);
  quoted.value = data.content || "";
  inReplyTo = data.name || null;
  await nextTick();
  emailRef.value?.focus();
}

/** Opens the email composer for a new email. */
function write() {
  mode.value = "email";
  if (!subject.value) subject.value = props.title || props.name;
  nextTick(() => emailRef.value?.focus());
}

defineExpose({ reply, write });
</script>
