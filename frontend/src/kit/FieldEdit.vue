<template>
  <!-- One field of a record, shown as the form shows it read-only, with a
       pencil (a chevron for a Link or Select) that puts the form's own
       control for it over the place it is shown. A Check is a box that sets
       the form's value. Nothing shows while the form hides the field. -->
  <div v-if="status && status !== 'None'" class="flex min-w-0 items-center gap-1.5" :class="[start ? 'justify-start' : 'justify-end', { 'w-full': editing }]">
    <Checkbox v-if="check" :model-value="Boolean(form.frm.value?.doc?.[field])" :disabled="!writable" :aria-label="label" @update:model-value="tick" />
    <div v-else-if="editing" ref="spot" class="w-full min-w-48" />
    <template v-else>
      <span v-if="long && shown" class="min-w-0 text-start [&_p]:mb-2" v-html="shown" />
      <span v-else class="min-w-0 truncate" :class="{ 'text-ink-gray-4': !shown }" v-html="shown || placeholder || '–'" />
      <button
        v-if="writable"
        type="button"
        class="shrink-0 rounded-2 text-ink-gray-4 hover:text-ink-gray-8 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        :aria-label="__('Change {0}', [label])"
        @click="start"
      >
        <span :class="PICKED.includes(fieldtype) ? 'lucide-chevron-down size-4' : 'lucide-pencil size-3.5'" class="block" aria-hidden="true" />
      </button>
    </template>
  </div>
  <div v-if="editing && long" class="mt-2 flex justify-end gap-2">
    <Button size="sm" :label="__('Cancel')" @click="cancel" />
    <Button variant="solid" size="sm" :label="__('Save')" @click="save" />
  </div>
</template>

<script setup>
// The standard way a page changes one field of a record (docs/STANDARD.md):
// the record's own desk form, out of sight (the kit's useForm), lends the
// field's control to the page while it is changed, and takes it back after.
// A change saves the form as desk saves it; Escape reloads it unchanged.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Button, Checkbox } from "frappe-ui";

import { __ } from "./desk";

const props = defineProps({
  // useForm's answer for the record.
  form: { type: Object, required: true },
  field: { type: String, required: true },
  label: { type: String, required: true },
  // What shows while it has no value.
  placeholder: String,
  // Set at the line's start, as long text is, not its end.
  start: Boolean,
});
const emit = defineEmits(["saved"]);

const PICKED = ["Link", "Select", "Dynamic Link", "Autocomplete"];
const LONG = ["Text Editor", "Small Text", "Text", "Long Text", "Markdown Editor"];

const spot = ref();
const editing = ref(false);
let lent = null;
let saving = false;
let stop = null;

const control = computed(() => props.form.control(props.field));
const status = computed(() => props.form.status(props.field));
const fieldtype = computed(() => control.value?.df.fieldtype);
const long = computed(() => LONG.includes(fieldtype.value));
const check = computed(() => fieldtype.value === "Check");
const writable = computed(() => status.value === "Write");
const shown = computed(() => (props.form.version.value, props.form.shown(props.field)));

async function start() {
  editing.value = true;
  await nextTick();
  lent = props.form.lend(props.field, spot.value, { keys, left });
  const c = lent?.control;
  (c?.$input || c?.quill)?.focus?.();
}

// A change to the field saves the form: a link or date picked, a number
// typed and left. Long text waits for Save.
async function save() {
  const frm = props.form.frm.value;
  if (!frm || saving) return;
  saving = true;
  try {
    if (frm.is_dirty()) await frm.save();
    if (frm.is_dirty()) return;
    emit("saved");
    close();
  } finally {
    saving = false;
  }
}

function close() {
  lent?.give_back();
  lent = null;
  editing.value = false;
}

function cancel() {
  const frm = props.form.frm.value;
  if (frm?.is_dirty()) frm.reload_doc();
  close();
}

function keys(e) {
  if (e.key === "Escape") {
    e.preventDefault();
    e.stopPropagation();
    return cancel();
  }
  if (e.key !== "Enter" || long.value) return;
  e.preventDefault();
  // The input's own change goes into the form first.
  lent?.control?.$input?.trigger("change");
  setTimeout(() => (props.form.frm.value?.is_dirty() ? save() : close()), 50);
}

// Leaving the field without a change puts it back.
function left() {
  if (long.value || !editing.value || saving) return;
  if (!props.form.frm.value?.is_dirty()) close();
}

// A box ticked is set through the form, which its scripts hear, then saved.
async function tick(on) {
  await props.form.set(props.field, on ? 1 : 0);
  save();
}

onMounted(() => {
  stop = props.form.edited((fieldname) => {
    if (fieldname === props.field && editing.value && !long.value) setTimeout(save, 0);
  });
});
onBeforeUnmount(() => {
  stop?.();
  lent?.give_back();
});
</script>
