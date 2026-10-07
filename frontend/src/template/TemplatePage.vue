<template>
  <Page wide>
    <Loading v-if="!said" />
    <!-- The template's tasks. Frappe's own form sidebar is on the page's
         right (onedesk.island_page). -->
    <div v-else class="pt-6">
      <!-- What the workspace's extensions add to the page (one_studio/places.py). -->
      <div ref="spot" class="empty:hidden [&_.one-place-spot]:mb-4" />
      <p class="text-base text-ink-gray-6" :class="agreed ? 'mb-1' : 'mb-4'">{{ summary }}</p>
      <p v-if="agreed" class="mb-4 text-base text-ink-gray-6">{{ agreed }}</p>
      <Tasks
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
  </Page>
</template>

<script setup>
// A project template's page (one_project/page/project_template_view): the
// template's tasks in the Tasks table in template mode. Desk's page head above
// it carries New Project, Edit Details and the form's own menu.
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { Loading, Page, __, call, can, confirm, follow, go, newDoc, onedesk, prompt, useRecord } from "../kit";
import Tasks from "./Tasks.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onStatus: Function,
  onActions: Function,
});

const METHOD = "onedesk.one_project.template_view";
const name = computed(() => props.route[0]);
const said = ref(null);
const record = useRecord("Project Template", name);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call(`${METHOD}.read`, { template: asked });
  if (asked !== name.value) return;
  said.value = got;
  report();
}

let stop = null;
watch(
  name,
  (now) => {
    stop?.();
    said.value = null;
    if (!now) return;
    // Every change saves the template, so whoever has it open hears it.
    stop = follow("Project Template", now, load);
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop?.());
watch(record.record, () => said.value && report());

const summary = computed(() => {
  const s = said.value;
  const tasks = s.tasks.filter((one) => !one.is_group).length;
  return [
    tasks === 1 ? __("1 task") : __("{0} tasks", [tasks]),
    s.days === 1 ? __("1 day") : __("{0} days", [s.days]),
    s.used ? (s.used === 1 ? __("Used by 1 project") : __("Used by {0} projects", [s.used])) : __("Not used yet"),
  ].join(" · ");
});

// What a project made from it starts with: its payment terms, terms and
// conditions and retention, set under Edit Details.
const agreed = computed(() => {
  const s = said.value;
  return [s.payment_terms, s.terms, s.retention ? __("{0}% retention", [s.retention]) : ""].filter(Boolean).join(" · ");
});

function report() {
  const s = said.value;
  props.onTitle?.(s.name);
  props.onStatus?.(s.disabled ? { label: __("Disabled"), color: "gray" } : null);
  extended(s);
  const actions = [];
  if (!s.disabled && can("create", "Project")) {
    actions.push({ label: __("New Project"), primary: true, onClick: () => newDoc("Project", { project_template: s.name, project_type: s.project_type }) });
  }
  actions.push({ label: __("Edit Details"), onClick: () => go(`/desk/project-template/${encodeURIComponent(s.name)}?edit=1`) });
  props.onActions?.([...actions, ...verbs, ...record.menu({ gone: () => go("/desk/project-template") })]);
}

// Each change is the server's (template_view.py); the page reads the template
// again once it is saved, and so does anybody else who has it open.
const run = (method, args) => call(`${METHOD}.${method}`, { template: name.value, ...args }).then(load);
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

// The workspace's extensions on the template's page (one_studio/places.py):
// those written for it are told the template, those written for a Project
// Template's head are told the record as its head is.
const spot = ref(null);
let verbs = [];
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  const doc = record.record.value?.doc;
  if (!places || !spot.value || !doc) return;
  const key = `${s.name}/${doc.modified}/${s.modified}`;
  if (drawn === key) return;
  drawn = key;
  spot.value.replaceChildren();
  verbs = [];
  const lend = () => places.spot(($spot) => $spot.appendTo(spot.value));
  if (places.listening("oneproject_template.template")) {
    const template = { name: s.name, project_type: s.project_type, tasks: s.tasks.length, days: s.days, used: s.used };
    places.emit("oneproject_template.template", { template }, lend());
  }
  if (places.listening("record_head.drawn")) {
    const page = lend();
    const said = [];
    places.emit(
      "record_head.drawn",
      Object.fromEntries(Object.entries(doc).filter(([field]) => !field.startsWith("__"))),
      {
        verb: (label, handler) => said.push({ label: String(label || ""), onClick: () => handler(), button: true }),
        figure: (label, value) => page.note(`${label} · ${value ?? ""}`, "gray"),
        note: page.note,
      },
      "Project Template"
    );
    verbs = said;
  }
}
</script>
