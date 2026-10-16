<template>
  <!-- A frappe web form (one/portal.py `form`), drawn with frappe-ui's
       controls and saved through frappe's own accept, which checks the
       reader may: its sections and columns as the form lays them out, Save
       and Discard in the head once something has changed. -->
  <Head :title="title" :crumbs="crumbs">
    <template #actions>
      <template v-if="dirty">
        <Button :label="__('Discard')" @click="discard" />
        <Button variant="solid" :label="__('Save')" :loading="saving" @click="save" />
      </template>
    </template>
  </Head>
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <Loading v-if="!said && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <form v-else class="flex flex-col gap-5" @submit.prevent="save">
      <Card v-for="(section, s) in sections" :key="s" :title="section.label || ''">
        <div class="grid gap-x-6 gap-y-4" :class="section.columns.length > 1 && 'sm:grid-cols-2'">
          <div v-for="(column, c) in section.columns" :key="c" class="flex flex-col gap-4">
            <template v-for="field in column" :key="field.fieldname">
              <div v-if="field.fieldtype === 'Attach Image'" class="flex flex-col gap-1.5">
                <span class="text-xs text-ink-gray-5">{{ field.label }}</span>
                <div class="flex items-center gap-3">
                  <Avatar :label="me.name" :image="values[field.fieldname]" size="2xl" />
                  <FileUploader :file-types="['image/*']" @success="(file) => (values[field.fieldname] = file.file_url)">
                    <template #default="{ openFileSelector, uploading }">
                      <Button :label="values[field.fieldname] ? __('Change') : __('Upload')" :loading="uploading" @click="openFileSelector" />
                    </template>
                  </FileUploader>
                  <Button v-if="values[field.fieldname]" variant="ghost" :label="__('Remove')" @click="values[field.fieldname] = ''" />
                </div>
              </div>
              <FormControl
                v-else
                v-model="values[field.fieldname]"
                :type="kinds[field.fieldtype] || 'text'"
                :label="field.label"
                :required="Boolean(field.reqd)"
                :options="choices(field)"
              />
            </template>
          </div>
        </div>
      </Card>
    </form>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { onBeforeRouteLeave, useRouter } from "vue-router";
import { Avatar, Button, FileUploader, FormControl, toast } from "frappe-ui";

import { call } from "../call";
import { __, boot } from "../words";
import Card from "./Card.vue";
import Empty from "./Empty.vue";
import Head from "./Head.vue";
import Loading from "./Loading.vue";

const props = defineProps({
  page: { type: String, required: true },
  name: { type: String, default: null },
  heading: { type: String, default: "" },
  crumbs: { type: Array, default: () => [] },
  // Where the reader goes once it is saved; staying put when unset.
  after: { type: String, default: "" },
});
const emit = defineEmits(["saved"]);
const router = useRouter();
const me = boot().me || {};

const kinds = { Select: "select", Autocomplete: "combobox", Check: "checkbox", "Small Text": "textarea", Text: "textarea" };
const said = ref(null);
const failed = ref(false);
const values = ref({});
const loaded = ref("{}");
const saving = ref(false);

const title = computed(() => props.heading || said.value?.title || "");
const dirty = computed(() => JSON.stringify(values.value) !== loaded.value);

// A web form's breaks, read in order: a Section Break starts a section, a
// Column Break a column in it.
const sections = computed(() => {
  const out = [{ label: "", columns: [[]] }];
  for (const field of said.value?.fields || []) {
    if (field.fieldtype === "Section Break") out.push({ label: field.label, columns: [[]] });
    else if (field.fieldtype === "Column Break") out.at(-1).columns.push([]);
    else if (field.fieldname) out.at(-1).columns.at(-1).push(field);
  }
  return out.filter((one) => one.columns.some((column) => column.length));
});

const choices = (field) =>
  (field.options || []).map((one) => (typeof one === "string" ? { label: one, value: one } : { label: one.label || one.value, value: one.value }));

function take(got) {
  said.value = got;
  const start = {};
  for (const field of got.fields) if (field.fieldname) start[field.fieldname] = got.doc[field.fieldname] ?? (field.fieldtype === "Check" ? 0 : "");
  values.value = start;
  loaded.value = JSON.stringify(start);
}

async function load() {
  said.value = null;
  failed.value = false;
  try {
    take(await call("form", { page: props.page, name: props.name }));
  } catch {
    failed.value = true;
  }
}

const discard = () => (values.value = JSON.parse(loaded.value));

async function save() {
  saving.value = true;
  try {
    const data = { ...values.value, ...(said.value.doc.name ? { name: said.value.doc.name } : {}) };
    await call("frappe.website.doctype.web_form.web_form.accept", { web_form: said.value.web_form, data: JSON.stringify(data) });
    loaded.value = JSON.stringify(values.value);
    toast.success(__("Saved"));
    emit("saved");
    if (props.after) router.push(props.after);
  } catch (error) {
    toast.error(error?.messages?.[0] || __("Couldn't save."));
  } finally {
    saving.value = false;
  }
}

// Leaving with unsaved changes asks first, as a desk form does.
const warn = (event) => {
  if (!dirty.value) return;
  event.preventDefault();
  event.returnValue = "";
};
window.addEventListener("beforeunload", warn);
onBeforeUnmount(() => window.removeEventListener("beforeunload", warn));
onBeforeRouteLeave(() => !dirty.value || window.confirm(__("You have unsaved changes. Leave anyway?")));

watch(() => [props.page, props.name], load, { immediate: true });
</script>
