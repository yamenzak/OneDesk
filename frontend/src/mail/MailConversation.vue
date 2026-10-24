<template>
  <div class="flex h-full min-h-0 flex-col">
    <div v-if="!messages.length" class="flex flex-1 flex-col items-center justify-center gap-2 text-ink-gray-5">
      <span class="lucide-mail-open size-6" aria-hidden="true" />
      <span class="text-base">{{ selected > 1 ? __("{0} conversations selected", [selected]) : __("No conversation selected") }}</span>
    </div>
    <div v-else ref="scroller" class="min-h-0 flex-1 overflow-auto">
      <div class="border-b border-outline-gray-1 px-5 py-3">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ messages[0].subject || __("(no subject)") }}</h2>
        <div v-if="records.length" class="mt-2 flex flex-wrap gap-1.5">
          <span
            v-for="row in records"
            :key="`${row.link_doctype}/${row.link_name}`"
            class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 py-0.5 pe-1 ps-2.5 text-sm"
            :title="[row.link_title, (FILED_BY[row.one_linked_by || 'contact'] || FILED_BY.contact)()].filter(Boolean).join(' · ')"
          >
            <a :href="recordRoute(row.link_doctype, row.link_name)" class="text-ink-gray-8 hover:underline">{{ __(row.link_doctype) }} {{ row.link_name }}</a>
            <button type="button" class="rounded-full p-0.5 text-ink-gray-5 hover:bg-surface-gray-3" :aria-label="__('Unlink')" :title="__('Unlink')" @click="unfile(row)">
              <span class="lucide-x size-3" aria-hidden="true" />
            </button>
          </span>
        </div>
        <PlaceSpot :said="placed" class="mt-2" />
      </div>

      <template v-for="(message, at) in messages" :key="message.name">
        <button
          v-if="folded(message, at)"
          type="button"
          class="flex w-full items-center gap-3 border-b border-outline-gray-1 px-5 py-2.5 text-start hover:bg-surface-gray-1"
          @click="unfolded.add(message.name)"
        >
          <MailFace :name="message.sender_full_name" :email="message.sender" :picture="message.face" />
          <span class="shrink-0 font-medium text-ink-gray-8">{{ message.sender_full_name || message.sender }}</span>
          <span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ message.snippet }}</span>
          <span class="shrink-0 text-sm text-ink-gray-5">{{ when(message.communication_date) }}</span>
        </button>
        <article v-else :ref="(el) => at === firstOpen && (openEl = el)" class="border-b border-outline-gray-1 px-5 py-4">
          <div class="flex items-start gap-3">
            <MailFace :name="message.sender_full_name" :email="message.sender" :picture="message.face" />
            <div class="min-w-0 flex-1 text-sm">
              <div>
                <span class="font-medium text-ink-gray-9">{{ message.sender_full_name || message.sender }}</span>
                <span v-if="message.sender_full_name" class="text-ink-gray-5"> &lt;{{ message.sender }}&gt;</span>
              </div>
              <div v-if="message.recipients" class="truncate text-ink-gray-6"><span class="text-ink-gray-5">{{ __("To") }}</span> {{ message.recipients }}</div>
              <div v-if="message.cc" class="truncate text-ink-gray-6"><span class="text-ink-gray-5">{{ __("Cc") }}</span> {{ message.cc }}</div>
            </div>
            <span class="shrink-0 text-sm text-ink-gray-5" :title="when(message.communication_date, true)">{{ when(message.communication_date) }}</span>
          </div>
          <MailBody :content="message.content" class="mt-3" />
          <div v-if="(message.attachments || []).length || (message.unsaved || []).length" class="mt-3 flex flex-wrap gap-2">
            <span v-for="file in message.attachments || []" :key="file.name" class="inline-flex items-center gap-1 rounded-3 border border-outline-gray-2 ps-2 text-sm">
              <a :href="file.file_url" target="_blank" rel="noopener" class="inline-flex min-w-0 items-center gap-1.5 py-1 text-ink-gray-8" :title="file.file_name">
                <span class="lucide-paperclip size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
                <span class="max-w-48 truncate">{{ file.file_name }}</span>
                <span class="text-ink-gray-5">{{ fileSize(file.file_size) }}</span>
              </a>
              <Button size="sm" variant="ghost" icon="lucide-folder-down" :aria-label="__('Save to My Files')" :title="__('Save to My Files')" @click="saveFile(file)" />
            </span>
            <span
              v-for="file in message.unsaved || []"
              :key="file.file_name"
              class="inline-flex items-center gap-1.5 rounded-3 border border-dashed border-outline-gray-3 px-2 py-1 text-sm text-ink-gray-6"
              :title="fullNote"
            >
              <span class="lucide-hard-drive size-3.5" aria-hidden="true" />{{ file.file_name }} · {{ __("Not saved, storage is full") }}
            </span>
          </div>
          <IntakePanel :message="message.name" class="mt-3" />
        </article>
      </template>

      <div class="flex flex-wrap gap-2 px-5 py-4">
        <Button variant="subtle" icon-left="lucide-reply" :label="__('Reply')" @click="emit('write', { reply: true })" />
        <Button variant="subtle" icon-left="lucide-reply-all" :label="__('Reply all')" @click="emit('write', { reply: true, all: true })" />
        <Button variant="subtle" icon-left="lucide-forward" :label="__('Forward')" @click="emit('write', { forward: true })" />
      </div>
    </div>
  </div>
</template>

<script setup>
// A conversation, its newest message open and the older ones read folded to
// a line; the records it is filed on, and reply, reply all and forward.
import { computed, nextTick, reactive, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { PlaceSpot, __, alert, call, dialog, fileSize, onedesk, recordRoute } from "../kit";
import IntakePanel from "../intake/IntakePanel.vue";
import { FILED_BY, when } from "./mail";
import MailBody from "./MailBody.vue";
import MailFace from "./MailFace.vue";

const props = defineProps({
  messages: { type: Array, default: () => [] },
  box: { type: Object, default: null },
  folder: { type: Object, default: null },
  selected: { type: Number, default: 0 },
});
const emit = defineEmits(["write"]);
defineExpose({ fileOn });

const fullNote = __("Storage is full. Saved automatically once there's space.");
const records = ref([]);
const unfolded = reactive(new Set());
const placed = reactive({ notes: [], actions: [] });
const scroller = ref(null);
let openEl = null;

const firstOpen = computed(() => props.messages.findIndex((one, at) => !folded(one, at)));
const folded = (message, at) => at < props.messages.length - 1 && message.seen && !unfolded.has(message.name);

async function loadRecords() {
  const names = props.messages.map((one) => one.name);
  if (!names.length) return (records.value = []);
  const got = await call("onedesk.one_mail.linking.links_of", { names });
  if (names[0] === props.messages[0]?.name) records.value = got;
}

watch(
  () => props.messages,
  async () => {
    unfolded.clear();
    loadRecords();
    tell();
    await nextTick();
    if (scroller.value) scroller.value.scrollTop = 0;
    if (openEl && props.messages.length > 1) openEl.scrollIntoView({ block: "start" });
  },
  { immediate: true }
);

function fileOn() {
  const kinds = onedesk().record_mail?.doctypes?.() || ["Customer", "Supplier", "Lead"];
  const asking = dialog({
    title: __("Link to Record"),
    fields: [
      { fieldname: "doctype", fieldtype: "Autocomplete", label: __("Record Type"), reqd: 1, options: kinds.map((one) => ({ value: one, label: __(one) })) },
      { fieldname: "docname", fieldtype: "Dynamic Link", options: "doctype", label: __("Record"), reqd: 1 },
    ],
    primary_action_label: __("Link"),
    primary_action: async (values) => {
      await call("onedesk.one_mail.linking.file", { names: props.messages.map((one) => one.name), doctype: values.doctype, docname: values.docname });
      asking.hide();
      loadRecords();
    },
  });
  asking.show();
}

async function unfile(row) {
  await call("onedesk.one_mail.linking.unfile", { names: props.messages.map((one) => one.name), doctype: row.link_doctype, docname: row.link_name });
  loadRecords();
}

async function saveFile(file) {
  await call("onedesk.one_storage.api.copy", { nodes: [file.name], target: "@my" });
  alert(__("Saved to My Files"));
}

// The conversation, for whatever else listens on this place
// (onedesk.places, "onemail.conversation").
function tell() {
  placed.notes = [];
  placed.actions = [];
  const places = onedesk().places;
  if (!props.messages.length || !places?.listening("onemail.conversation")) return;
  places.emit(
    "onemail.conversation",
    {
      subject: props.messages[0].subject || "",
      mailbox: props.box?.email || "",
      folder: props.folder?.kind || "",
      messages: props.messages.map((one) => ({
        sender: one.sender,
        sender_full_name: one.sender_full_name,
        recipients: one.recipients,
        cc: one.cc,
        subject: one.subject,
        date: one.communication_date,
        sent_or_received: one.sent_or_received,
        has_attachment: !!one.has_attachment,
        reference_doctype: one.reference_doctype,
        reference_name: one.reference_name,
      })),
    },
    {
      note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
      action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
    }
  );
}
</script>
