<template>
  <div class="max-w-md rounded-4 border border-outline-gray-2 bg-surface-elevation-1 p-3" data-tour="onechat-card">
    <div class="flex items-center gap-2">
      <span class="text-base font-medium text-ink-gray-9">{{ __(card.doctype) }}</span>
      <span v-if="card.record" class="truncate text-sm text-ink-gray-5">{{ card.record }}</span>
      <Badge class="ms-auto" :label="state.label" :theme="state.theme" size="sm" />
    </div>
    <dl v-if="card.fields.length" class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
      <template v-for="field in card.fields" :key="field.fieldname">
        <dt class="text-ink-gray-5">{{ field.label || field.fieldname }}</dt>
        <dd class="truncate text-ink-gray-8">{{ field.value ?? "—" }}</dd>
      </template>
    </dl>
    <p v-if="card.why && card.level === 'Proposed'" class="mt-2 whitespace-pre-line text-sm text-ink-gray-6">{{ card.why }}</p>
    <div v-if="card.level === 'Proposed' && card.may_decide" class="mt-3 flex justify-end gap-2">
      <Button size="sm" variant="ghost" :label="__('Dismiss')" :disabled="busy" @click="decide('dismiss')" />
      <Button size="sm" :label="__('Change')" :disabled="busy || !card.fields.length" @click="change" />
      <Button size="sm" variant="solid" :label="__('Approve')" :loading="busy" @click="decide('approve')" />
    </div>
    <div v-else-if="card.level === 'Done' && card.record" class="mt-3 flex justify-end">
      <Button size="sm" :label="__('Open {0}', [__(card.doctype)])" @click="goTo('Form', card.doctype, card.record)" />
    </div>
  </div>
</template>

<script setup>
// An agent's Draft or Ask First (one_chat/cards.py): Approve and Dismiss
// are the door's own approval (reading/act.py settle); Change edits what
// it proposes before it is approved.
import { computed, ref } from "vue";
import { Badge, Button } from "frappe-ui";

import { __, alert, call, dialog, goTo } from "../kit";
import { method } from "./chat";

const props = defineProps({ card: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const busy = ref(false);

const STATES = {
  Proposed: { label: __("Waiting"), theme: "amber" },
  Done: { label: __("Draft"), theme: "blue" },
  Dismissed: { label: __("Dismissed"), theme: "gray" },
  Refused: { label: __("Refused"), theme: "red" },
  Undone: { label: __("Undone"), theme: "gray" },
};
const state = computed(() => STATES[props.card.level] || { label: props.card.level, theme: "gray" });

async function decide(how) {
  busy.value = true;
  try {
    const done = await call(method(how), { action: props.card.name });
    alert(how === "approve" ? __("Approved") : __("Dismissed"));
    emit("changed", { ...props.card, level: done.level });
  } finally {
    busy.value = false;
  }
}

function change() {
  const shown = dialog({
    title: __("Change {0}", [__(props.card.doctype)]),
    fields: props.card.fields.map((field) => ({ fieldname: field.fieldname, fieldtype: "Data", label: field.label || field.fieldname, default: field.value })),
    primary_action_label: __("Save"),
    primary_action: async (values) => {
      const card = await call(method("change"), { action: props.card.name, values });
      shown.hide();
      emit("changed", card);
    },
  });
  shown.show();
}
</script>
