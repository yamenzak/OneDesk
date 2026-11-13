<template>
  <div v-if="status && status !== 'None'" class="flex min-w-0 items-center gap-1.5" :class="[start ? 'justify-start' : 'justify-end', { 'w-full': editing }]">
    <Switch v-if="check" :model-value="checked" :disabled="!writable" :aria-label="label" @update:model-value="tick" />
    <div v-else-if="editing" ref="spot" class="w-full min-w-48" />
    <template v-else>
      <span v-if="long && shown" class="min-w-0 text-start [&_p]:mb-2" v-html="shown" />
      <span v-else class="min-w-0 truncate" :class="{ 'text-ink-gray-4': !shown }" v-html="shown || placeholder || '–'" />
      <img v-if="touched" :src="oneaiMark" class="size-3.5 shrink-0" :alt="name('one_ai')" :title="__('Written by {0}', [name('one_ai')])" />
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Button, Switch } from "frappe-ui";

import { __, aiLeft, name, oneaiMark, oneaiOn } from "./desk";

const props = defineProps({
  form: { type: Object, required: true },
  field: { type: String, required: true },
  label: { type: String, required: true },
  placeholder: String,
  start: Boolean,
  table: String,
  row: String,
  blankZero: Boolean,
  hold: Boolean,
});
const emit = defineEmits(["saved", "cancel"]);

const PICKED = ["Link", "Select", "Dynamic Link", "Autocomplete"];
const LONG = ["Text Editor", "Small Text", "Text", "Long Text", "Markdown Editor"];

const spot = ref();
const editing = ref(false);
let lent = null;
let saving = false;
let stop = null;

const source = computed(() => (props.table ? props.form.row(props.table, props.row) : props.form));
const status = computed(() => source.value.status(props.field));
const fieldtype = computed(() => source.value.df(props.field)?.fieldtype);
const long = computed(() => LONG.includes(fieldtype.value));
const check = computed(() => fieldtype.value === "Check");
const writable = computed(() => status.value === "Write");
const shown = computed(() => {
  props.form.version.value;
  if (props.blankZero && !Number(source.value.value(props.field) || 0)) return "";
  return source.value.shown(props.field);
});
const ai = computed(() => !props.table && oneaiOn());
const words = (value) => String(value ?? "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
// Still what OneAI put there: the same comparison a desk form makes.
const touched = computed(() => {
  props.form.version.value;
  const doc = props.form.frm.value?.doc;
  const written = doc?.__onload?.ai_touched?.[props.field];
  return !props.table && written !== undefined && words(source.value.value(props.field)) === words(written);
});

// A long text left for the OneAI dial is what the panel writes in.
function noted() {
  const doc = props.form.frm.value?.doc;
  if (!doc || !long.value || !writable.value || !ai.value) return;
  aiLeft({
    doctype: doc.doctype,
    name: doc.__islocal ? "" : doc.name,
    fieldname: props.field,
    label: props.label,
    value: source.value.value(props.field) || "",
  });
}

const checked = computed(() => (props.form.version.value, Boolean(Number(source.value.value(props.field) || 0))));

async function start() {
  editing.value = true;
  await nextTick();
  lent = source.value.lend(props.field, spot.value, { keys, left });
  lent?.control?.$wrapper?.off("focusout.oneai").on("focusout.oneai", noted);
  const c = lent?.control;
  (c?.$input || c?.quill)?.focus?.();
}

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
  if (props.hold) return emit("cancel");
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
  if (e.key !== "Enter" || long.value || props.hold) return;
  e.preventDefault();
  lent?.control?.$input?.trigger("change");
  setTimeout(() => (props.form.frm.value?.is_dirty() ? save() : close()), 50);
}

function left() {
  if (long.value || props.hold || !editing.value || saving) return;
  if (!props.form.frm.value?.is_dirty()) close();
}

async function tick(on) {
  await source.value.set(props.field, on ? 1 : 0);
  save();
}

onMounted(() => {
  stop = props.form.edited((fieldname, row) => {
    if (fieldname !== props.field || (row || null) !== (props.row || null)) return;
    if (props.table) lent?.control?.set_formatted_input?.(source.value.value(props.field));
    if (editing.value && !long.value && !props.hold) setTimeout(save, 0);
  });
  if (props.hold && writable.value) start();
});
onBeforeUnmount(() => {
  stop?.();
  lent?.give_back();
});
</script>
