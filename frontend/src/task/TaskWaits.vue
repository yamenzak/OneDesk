<template>
  <div class="flex flex-col gap-1.5">
    <div v-for="one in rows" :key="one.row" class="flex min-w-0 items-center gap-2">
      <button class="flex min-w-0 items-center gap-2 text-start text-base hover:underline" @click="emit('open', one.name)">
        <span class="lucide-circle-check size-4 shrink-0" :class="one.done ? 'text-ink-green-3' : 'text-ink-gray-4'" aria-hidden="true" />
        <span class="truncate" :class="one.done ? 'text-ink-gray-5' : 'text-ink-gray-8'">{{ one.subject }}</span>
      </button>
      <Button v-if="writable" variant="ghost" size="sm" icon="lucide-x" class="shrink-0" :aria-label="__('Remove {0}', [one.subject])" @click="remove(one.row)" />
    </div>
    <p v-if="!rows.length && !adding" class="text-base text-ink-gray-5">{{ __("Nothing") }}</p>
    <template v-if="adding">
      <FieldEdit :form="form" table="depends_on" :row="adding" field="task" :label="__('Task')" hold start class="text-base text-ink-gray-8" @cancel="cancel" />
      <div class="flex gap-2">
        <Button size="sm" :label="__('Cancel')" @click="cancel" />
        <Button variant="solid" size="sm" :label="__('Save')" :loading="saving" @click="save" />
      </div>
    </template>
    <Button v-else-if="writable" variant="ghost" size="sm" class="-ms-2 self-start" icon-left="lucide-plus" :label="__('Add')" @click="add" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";

import { FieldEdit, __ } from "../kit";

const props = defineProps({ form: { type: Object, required: true }, about: { type: Function, required: true } });
const emit = defineEmits(["open", "saved"]);

const adding = ref(null);
const saving = ref(false);

const writable = computed(() => props.form.status("depends_on") === "Write");
const rows = computed(() =>
  (props.form.value("depends_on") || [])
    .filter((one) => one.task && one.name !== adding.value)
    .map((one) => {
      const known = props.about(one);
      return known && { row: one.name, name: one.task, ...known };
    })
    .filter(Boolean)
);

function add() {
  cancel();
  adding.value = props.form.addRow("depends_on");
}

async function save() {
  if (!props.form.row("depends_on", adding.value).value("task")) return cancel();
  saving.value = true;
  try {
    if (!(await props.form.save())) return;
    adding.value = null;
    emit("saved");
  } finally {
    saving.value = false;
  }
}

function cancel() {
  if (!adding.value) return;
  adding.value = null;
  props.form.discard();
}

async function remove(row) {
  cancel();
  props.form.removeRow("depends_on", row);
  if (await props.form.save()) emit("saved");
}
</script>
