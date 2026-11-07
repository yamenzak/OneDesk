<template>
  <div class="flex flex-col rounded-6 border border-outline-gray-2 py-1 text-sm">
    <div v-if="team.said.shared">
      <div class="flex h-8.5 items-center gap-2.5 px-4">
        <span class="lucide-users size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-ink-gray-6">{{ __("Assign") }}</span>
        <Dropdown :options="team.assignTo">
          <template #trigger><Button size="sm" variant="ghost" icon="lucide-plus" :aria-label="__('Assign')" :title="__('Assign')" /></template>
        </Dropdown>
      </div>
      <div v-if="team.said.assigned.length" class="flex flex-wrap gap-1.5 pb-2 pe-4 ps-10.5">
        <span v-for="one in team.said.assigned" :key="one.user" class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 py-0.5 pe-2.5 ps-0.5 text-ink-gray-8">
          <Avatar :label="one.name" :image="one.image" size="xs" />{{ one.name }}
        </span>
      </div>
    </div>
    <div>
      <div class="flex h-8.5 items-center gap-2.5 px-4">
        <span class="lucide-link size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-ink-gray-6">{{ __("Linked To") }}</span>
        <Button size="sm" variant="ghost" icon="lucide-plus" :aria-label="__('Link to Record')" :title="__('Link to Record')" @click="emit('link')" />
      </div>
      <div v-if="records.length" class="flex flex-wrap gap-1.5 pb-2 pe-4 ps-10.5">
        <span
          v-for="row in records"
          :key="`${row.link_doctype}/${row.link_name}`"
          class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 py-0.5 pe-1 ps-2.5"
          :title="[row.link_title, (FILED_BY[row.one_linked_by || 'contact'] || FILED_BY.contact)()].filter(Boolean).join(' · ')"
        >
          <a :href="recordRoute(row.link_doctype, row.link_name)" class="text-ink-gray-9 hover:underline">{{ __(row.link_doctype) }} {{ row.link_name }}</a>
          <button type="button" class="rounded-full p-0.5 text-ink-gray-5 hover:bg-surface-gray-3" :aria-label="__('Unlink')" :title="__('Unlink')" @click="emit('unlink', row)">
            <span class="lucide-x size-3" aria-hidden="true" />
          </button>
        </span>
      </div>
    </div>
    <div v-if="team.makeOptions.length" class="flex h-8.5 items-center gap-2.5 px-4">
      <span class="lucide-file-plus size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
      <span class="flex-1 text-ink-gray-6">{{ __("Create") }}</span>
      <Dropdown :options="team.makeOptions">
        <template #trigger><Button size="sm" variant="ghost" icon="lucide-chevron-down" :aria-label="__('Create')" :title="__('Create')" /></template>
      </Dropdown>
    </div>
    <div>
      <div class="flex h-8.5 items-center gap-2.5 px-4">
        <span class="lucide-bell-ring size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-ink-gray-6">{{ __("Remind Me") }}</span>
        <Dropdown :options="team.remindOptions">
          <template #trigger><Button size="sm" variant="ghost" icon="lucide-chevron-down" :aria-label="__('Remind Me')" :title="__('Remind Me')" /></template>
        </Dropdown>
      </div>
      <div v-if="team.said.remind_at" class="pb-2 pe-4 ps-10.5 text-ink-gray-6">{{ __("Reminder {0}", [dateTime(team.said.remind_at)]) }}</div>
    </div>

    <div class="mx-4 my-1 border-t border-outline-gray-1" />
    <MailSender :address="address" class="px-4 py-2" />

    <template v-if="team.said.shared">
      <div class="mx-4 my-1 border-t border-outline-gray-1" />
      <div class="flex h-8.5 items-center gap-2.5 px-4">
        <span class="lucide-message-square size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="flex-1 text-ink-gray-6">{{ __("Notes for the Team") }}</span>
        <span v-if="team.said.notes.length" class="text-ink-gray-5">{{ team.said.notes.length }}</span>
      </div>
      <div class="px-4 pb-2">
        <TextInput v-model="typed" :placeholder="__('Add a note')" @keydown.enter.prevent="note" />
        <p v-if="!team.said.notes.length" class="pt-2 text-ink-gray-5">{{ __("Never sent to anybody outside.") }}</p>
        <div v-for="one in team.said.notes" :key="one.name" class="flex gap-2 pt-3">
          <Avatar :label="one.by" size="xs" class="mt-0.5 shrink-0" />
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-2">
              <span class="min-w-0 flex-1 truncate font-medium text-ink-gray-9">{{ one.by }}</span>
              <span class="shrink-0 text-ink-gray-5">{{ ago(one.creation) }}</span>
            </div>
            <div class="text-ink-gray-8" v-html="one.content" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// Beside a conversation, as a record's panel is beside a record: who has it,
// what it is linked to, what to make from it and when to be reminded, then who
// wrote with their open records, then the team's notes.
import { ref } from "vue";
import { Avatar, Button, Dropdown, TextInput } from "frappe-ui";

import { __, ago, call, dateTime, escape, recordRoute } from "../kit";
import { FILED_BY } from "./mail";
import MailSender from "./MailSender.vue";

const props = defineProps({
  team: { type: Object, required: true },
  records: { type: Array, default: () => [] },
  address: { type: String, default: "" },
  account: { type: String, required: true },
  thread: { type: String, required: true },
});
const emit = defineEmits(["link", "unlink"]);
const typed = ref("");

async function note() {
  if (!typed.value.trim()) return;
  props.team.take(await call("onedesk.one_mail.team.note", { account: props.account, thread: props.thread, content: escape(typed.value.trim()) }));
  typed.value = "";
}
</script>
