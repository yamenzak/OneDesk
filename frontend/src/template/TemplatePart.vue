<template>
  <div class="text-ink-gray-8">
    <Loading v-if="!said" />
    <Tasks
      v-else
      :tasks="said.tasks"
      :can-write="said.can_write"
      @change="change"
      @add="add"
      @under="under"
      @nest="nest"
      @wait="wait"
      @remove="remove"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from "vue";

import { Loading, __, call, confirm, follow, prompt } from "../kit";
import Tasks from "./Tasks.vue";

const props = defineProps({ template: { type: String, required: true }, frm: { type: Object, default: null } });

const METHOD = "onedesk.one_project.template_view";
const said = ref(null);

async function load() {
  const asked = props.template;
  const got = await call(`${METHOD}.read`, { template: asked });
  if (asked === props.template) said.value = got;
}

let stop = null;
watch(
  () => props.template,
  (now) => {
    stop?.();
    said.value = null;
    stop = follow("Project Template", now, load);
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop?.());

const run = (method, args) => call(`${METHOD}.${method}`, { template: props.template, ...args }).then(load);
const change = (task, field, value) => run("change", { task, field, value });
const add = (subject, parent) => run("add", { subject, parent });
const nest = (task, parent) => run("nest", { task, parent });
const wait = (task, on, waits) => run("wait", { task, on, waits });
function under(parent) {
  prompt(
    { fieldtype: "Data", fieldname: "subject", label: __("Task"), reqd: 1 },
    ({ subject }) => add(subject, parent),
    __("Add Task Under"),
    __("Add Task")
  );
}
function remove(task) {
  const one = said.value.tasks.find((t) => t.name === task);
  confirm(__("Delete {0} and the tasks under it?", [one?.subject || task]), () => run("remove", { task }));
}
</script>
