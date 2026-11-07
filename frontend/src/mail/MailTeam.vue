<template>
  <div class="flex flex-wrap items-center gap-1">
    <Dropdown v-if="said.shared" :options="assignTo">
      <template #trigger>
        <Button size="sm" variant="ghost" :title="__('Assign')">
          <template #prefix><span :class="said.assigned.length ? 'lucide-user-check' : 'lucide-user-plus'" class="size-4" aria-hidden="true" /></template>
          {{ said.assigned.length ? said.assigned.map((one) => one.name).join(", ") : __("Assign") }}
        </Button>
      </template>
    </Dropdown>
    <Button
      size="sm"
      :variant="said.status === 'Done' ? 'subtle' : 'ghost'"
      :icon-left="said.status === 'Done' ? 'lucide-circle-check' : 'lucide-circle'"
      :label="said.status === 'Done' ? __('Done') : __('Mark Done')"
      :title="said.status === 'Done' ? __('Open Again') : __('Mark Done')"
      :aria-label="said.status === 'Done' ? __('Open Again') : __('Mark Done')"
      @click="toggleDone"
    />
    <Dropdown :options="snoozeOptions">
      <template #trigger>
        <Button size="sm" :variant="said.snoozed_until ? 'subtle' : 'ghost'" icon="lucide-alarm-clock" :title="said.snoozed_until ? __('Snoozed until {0}', [dateTime(said.snoozed_until)]) : __('Snooze')" :aria-label="__('Snooze')" />
      </template>
    </Dropdown>
    <Dropdown :options="remindOptions">
      <template #trigger>
        <Button size="sm" :variant="said.remind_at ? 'subtle' : 'ghost'" icon="lucide-bell-ring" :title="said.remind_at ? __('Reminder {0}', [dateTime(said.remind_at)]) : __('Remind Me')" :aria-label="__('Remind Me')" />
      </template>
    </Dropdown>
    <Dropdown v-if="makeOptions.length" :options="makeOptions">
      <template #trigger><Button size="sm" variant="ghost" icon="lucide-file-plus" :title="__('Create')" :aria-label="__('Create')" /></template>
    </Dropdown>
    <span v-if="replying.length" class="ms-1 inline-flex items-center gap-1 text-sm text-ink-amber-6">
      <span class="lucide-pen-line size-3.5" aria-hidden="true" />{{ __("{0} is writing a reply", [replying.join(", ")]) }}
    </span>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dropdown } from "frappe-ui";

import { __, asDateTime, call, can, dateTime, dialog, prompt, toast } from "../kit";

const props = defineProps({
  account: { type: String, required: true },
  thread: { type: String, required: true },
  replying: { type: Array, default: () => [] },
  make: { type: Function, default: null },
});
const emit = defineEmits(["changed", "state"]);

const TEAM = "onedesk.one_mail.team.";
const said = ref({ shared: false, assigned: [], notes: [], people: [], status: "Open" });

async function load() {
  said.value = await call(TEAM + "state", { account: props.account, thread: props.thread });
  emit("state", said.value);
}
watch(() => [props.account, props.thread], load, { immediate: true });

async function act(method, args, message) {
  said.value = await call(TEAM + method, { account: props.account, thread: props.thread, ...args });
  emit("state", said.value);
  if (message) toast(message);
  emit("changed");
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

function choose(title, options, done) {
  const asking = dialog({
    title,
    fields: [{ fieldname: "choice", fieldtype: "Select", label: title, options: options.map((one) => one.label).join("\n"), reqd: 1 }],
    primary_action_label: __("Save"),
    primary_action: ({ choice }) => {
      asking.hide();
      done(options.find((one) => one.label === choice));
    },
  });
  asking.show();
}

const toggleDone = () => act("done", { done: said.value.status === "Done" ? 0 : 1 }, said.value.status === "Done" ? __("Opened again.") : __("Marked done."));
const snoozeNow = () => choose(__("Snooze"), snoozeOptions.value, (one) => one?.onClick());
const assignNow = () => said.value.shared && choose(__("Assign"), assignTo.value, (one) => one?.onClick());

function take(state) {
  said.value = state;
}

defineExpose({ load, toggleDone, snoozeNow, assignNow, take });
</script>
