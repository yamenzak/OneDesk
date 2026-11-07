<template>
  <div class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center gap-1.5">
      <Dropdown v-if="said.shared" :options="assignTo">
        <template #trigger>
          <Button size="sm" variant="subtle" :icon-left="said.assigned.length ? 'lucide-user-check' : 'lucide-user-plus'" :label="said.assigned.length ? said.assigned.map((one) => one.name).join(', ') : __('Assign')" />
        </template>
      </Dropdown>
      <Button
        size="sm"
        :variant="said.status === 'Done' ? 'solid' : 'subtle'"
        :icon-left="said.status === 'Done' ? 'lucide-circle-check' : 'lucide-circle'"
        :label="said.status === 'Done' ? __('Done') : __('Mark Done')"
        @click="act('done', { done: said.status === 'Done' ? 0 : 1 })"
      />
      <Dropdown :options="snoozeOptions">
        <template #trigger>
          <Button size="sm" variant="subtle" icon-left="lucide-alarm-clock" :label="said.snoozed_until ? __('Snoozed until {0}', [dateTime(said.snoozed_until)]) : __('Snooze')" />
        </template>
      </Dropdown>
      <Dropdown :options="remindOptions">
        <template #trigger>
          <Button size="sm" variant="subtle" icon-left="lucide-bell-ring" :label="said.remind_at ? __('Reminder {0}', [dateTime(said.remind_at)]) : __('Remind Me')" />
        </template>
      </Dropdown>
      <Dropdown v-if="makeOptions.length" :options="makeOptions">
        <template #trigger><Button size="sm" variant="subtle" icon-left="lucide-plus" :label="__('Create')" /></template>
      </Dropdown>
    </div>
    <p v-if="replying.length" class="flex items-center gap-1.5 text-sm text-ink-amber-6">
      <span class="lucide-pen-line size-3.5" aria-hidden="true" />{{ __("{0} is writing a reply", [replying.join(", ")]) }}
    </p>
    <div v-if="said.shared && (said.notes.length || noting)" class="flex flex-col gap-1.5 rounded-3 bg-surface-amber-1 px-3 py-2">
      <div v-for="one in said.notes" :key="one.name" class="text-sm">
        <span class="font-medium text-ink-gray-8">{{ one.by }}</span>
        <span class="ms-1.5 text-ink-gray-5">{{ ago(one.creation) }}</span>
        <div class="text-ink-gray-8" v-html="one.content" />
      </div>
      <div v-if="noting" class="flex items-end gap-1.5">
        <TextInput v-model="typed" class="flex-1" :placeholder="__('Note for the team, never sent')" @keydown.enter.prevent="save" />
        <Button size="sm" variant="solid" :label="__('Add Note')" :disabled="!typed.trim()" @click="save" />
      </div>
    </div>
    <button v-if="said.shared && !noting" type="button" class="self-start text-sm text-ink-gray-5 hover:underline" @click="noting = true">{{ __("Add a note for the team") }}</button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dropdown, TextInput } from "frappe-ui";

import { __, ago, asDateTime, call, can, dateTime, escape, prompt, toast } from "../kit";

const props = defineProps({
  account: { type: String, required: true },
  thread: { type: String, required: true },
  replying: { type: Array, default: () => [] },
  make: { type: Function, default: null },
});
const emit = defineEmits(["changed"]);

const TEAM = "onedesk.one_mail.team.";
const said = ref({ shared: false, assigned: [], notes: [], people: [], status: "Open" });
const noting = ref(false);
const typed = ref("");

async function load() {
  said.value = await call(TEAM + "state", { account: props.account, thread: props.thread });
  noting.value = false;
}
watch(() => [props.account, props.thread], load, { immediate: true });

async function act(method, args, message) {
  said.value = await call(TEAM + method, { account: props.account, thread: props.thread, ...args });
  if (message) toast(message);
  emit("changed");
}

async function save() {
  if (!typed.value.trim()) return;
  await act("note", { content: escape(typed.value.trim()) });
  typed.value = "";
}

const assignTo = computed(() => [
  ...said.value.people.map((one) => ({ label: one.name, onClick: () => act("assign", { user: one.user }, __("Assigned to {0}.", [one.name])) })),
  ...(said.value.assigned.length ? [{ label: __("Nobody"), icon: "lucide-user-x", onClick: () => act("assign", { user: null }, __("Unassigned.")) }] : []),
]);

const at = (days, hour) => {
  const when = new Date();
  when.setDate(when.getDate() + days);
  when.setHours(hour, 0, 0, 0);
  return asDateTime(when);
};
const later = () => {
  const when = new Date(Date.now() + 3 * 3600 * 1000);
  when.setMinutes(0, 0, 0);
  return asDateTime(when);
};
const nextMonday = () => {
  const days = ((8 - new Date().getDay()) % 7) || 7;
  return at(days, 8);
};

function pick(title, done) {
  prompt({ fieldname: "at", fieldtype: "Datetime", label: __("When"), reqd: 1 }, ({ at: chosen }) => done(chosen), title, __("Save"));
}

const snoozeOptions = computed(() => [
  { label: __("Later Today"), onClick: () => act("snooze", { until: later() }, __("Snoozed.")) },
  { label: __("Tomorrow Morning"), onClick: () => act("snooze", { until: at(1, 8) }, __("Snoozed.")) },
  { label: __("Next Week"), onClick: () => act("snooze", { until: nextMonday() }, __("Snoozed.")) },
  { label: __("Pick a Time"), onClick: () => pick(__("Snooze Until"), (until) => act("snooze", { until }, __("Snoozed."))) },
  ...(said.value.snoozed_until ? [{ label: __("Back to Inbox Now"), onClick: () => act("snooze", { until: null }) }] : []),
]);

const remindOptions = computed(() => [
  { label: __("In 1 Day"), onClick: () => act("remind", { at: at(1, 9) }, __("Reminder set.")) },
  { label: __("In 3 Days"), onClick: () => act("remind", { at: at(3, 9) }, __("Reminder set.")) },
  { label: __("In a Week"), onClick: () => act("remind", { at: at(7, 9) }, __("Reminder set.")) },
  { label: __("Pick a Time"), onClick: () => pick(__("Remind Me"), (when) => act("remind", { at: when }, __("Reminder set."))) },
  ...(said.value.remind_at ? [{ label: __("No Reminder"), onClick: () => act("remind", { at: null }) }] : []),
]);

const MAKES = ["Lead", "Opportunity", "Issue", "Task", "Non Conformance", "Purchase Order"];
const makeOptions = computed(() => (props.make ? MAKES.filter((one) => can("create", one)).map((one) => ({ label: __(one), onClick: () => props.make(one) })) : []));

defineExpose({ load });
</script>
