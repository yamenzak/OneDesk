<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <Header :said="said" @change="changeProject" @media="load" @view="(now) => (view = now)" />
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="tab" :views="VIEWS" class="mt-4" />
      <div ref="views" class="pt-4 transition-[padding] duration-200" :style="{ paddingInlineEnd: `${room}px` }">
      <div v-if="taskView" class="flex flex-wrap items-center gap-2 pb-2">
        <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
          <span class="lucide-list-checks size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Tasks") }}
          <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
        </h2>
        <TabButtons v-model="view" :options="LAYOUTS" />
        <TextInput v-model="search" size="sm" class="w-44 max-md:order-last max-md:w-full" :placeholder="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
        </TextInput>
        <Dropdown v-if="view === 'tasks' || view === 'timeline'" :options="groupChoices">
          <template #trigger><Button size="sm" icon-left="lucide-rows-3" :label="__('Group by {0}', [groupLabel])" /></template>
        </Dropdown>
        <Button size="sm" :variant="showDone ? 'subtle' : 'ghost'" icon-left="lucide-circle-check" :label="__('Done')" @click="showDone = !showDone" />
        <Dropdown v-if="templates.length" :options="templates">
          <template #trigger><Button size="sm" icon-left="lucide-layout-template" :label="__('Project Template')" /></template>
        </Dropdown>
        <Button v-if="work?.can_create" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Task')" @click="newTask" />
      </div>

      <Overview v-if="view === 'overview'" :said="said" :writing="writing" @changed="load" @view="(now) => (view = now)" @main="only = true" />
      <template v-else-if="taskView">
        <PlaceSpot :said="taskSpot" class="mb-3" />
        <Loading v-if="!work" />
        <Tasks v-else-if="view === 'tasks'" :current="opened?.name" :work="work" :groups="groups" :team="team" :can-write="work.can_write" @open="open" @set="set" @give="give" @take="take" @add="add" />
        <Board v-else-if="view === 'board'" :work="work" :tasks="shown" :show-done="showDone" :can-write="work.can_write" @open="open" @set="set" />
        <Timeline v-else :work="work" :groups="groups" @open="open" />
      </template>
      <Time v-else-if="view === 'time'" :project-name="said.name" :customer="said.customer" :title="said.title" :tree="tree" />
      <Money v-else-if="view === 'money'" :said="said" @changed="load" @view="(now) => (view = now)" />
      <Invoices v-else-if="view === 'invoices'" :project-name="said.name" :project-title="said.title" :kind="said.kind" :customer="said.customer" :currency="said.currency" />
      <Team v-else-if="view === 'team'" :project-name="said.name" :modified="said.modified" @changed="load" />
      <Suppliers v-else-if="view === 'suppliers'" :said="said" />
      <Files v-else-if="view === 'files'" :project="said.name" @count="(n) => (fileCount = n)" />
      <ProjectActivity v-else-if="view === 'activity'" :key="said.name" :project="said.name" :modified="said.modified" @task="open" />
      </div>

      <TaskPanel :task="opened" :work="work || EMPTY" :team="team" :can-write="work?.can_write" @close="opened = null" @set="set" @give="give" @take="take" @open="open" @add="add" @changed="loadWork" />
    </template>
  </Page>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, Dropdown, TabButtons, TextInput } from "frappe-ui";

import { Loading, Page, PlaceSpot, ViewTabs, __, andList, call, can, confirm, escape, follow, followList, go, listen, newDoc, onResize, onedesk, setQuery, setValue, useRecord, viewWidth } from "../kit";
import Board from "./Board.vue";
import Files from "./Files.vue";
import Header from "./Header.vue";
import Invoices from "./Invoices.vue";
import Money from "./Money.vue";
import Overview from "./Overview.vue";
import Suppliers from "./Suppliers.vue";
import TaskPanel from "./TaskPanel.vue";
import Team from "./Team.vue";
import Tasks from "./Tasks.vue";
import Time from "./Time.vue";
import Timeline from "./Timeline.vue";
import { groupTasks, visible } from "./group";
import { onlyArg, provideOnly } from "./only";
import { usePlace } from "./place";
import { useWork } from "./useWork";

const ProjectActivity = defineAsyncComponent(() => import("./ProjectActivity.vue"));

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onStatus: Function,
  onActions: Function,
});

const EMPTY = { statuses: [], priorities: [], people: {}, groups: [], tasks: [] };
const name = computed(() => props.route[0]);
const said = ref(null);
const view = ref(props.query.view || "overview");
const search = ref("");
const showDone = ref(false);
const groupBy = ref("project");
const fileCount = ref(null);
const opened = ref(null);
const only = ref(props.query.only === "1");
provideOnly(only);

const { work, load: loadWork, set, add: addTask, give, take, find, count } = useWork(name, only);
const record = useRecord("Project", name);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_project.view.said", { project: asked, ...onlyArg(only) });
  if (asked !== name.value) return;
  said.value = got;
  report();
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
let stop = [];
watch(
  name,
  (now) => {
    stop.forEach((one) => one());
    said.value = null;
    opened.value = null;
    if (!now) return;
    stop = [
      follow("Project", now, load),
      listen("one_project_money", (data) => data.project === now && load()),
      listen("one_project_media", (data) => data.project === now && load()),
      ...["Sales Order", "Quotation", "Employee", "User"].map((one) => followList(one, soon)),
    ];
    load();
    loadWork();
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(view, (now) => setQuery("view", now === "overview" ? null : now));
watch(only, (now) => {
  setQuery("only", now ? "1" : null);
  said.value = null;
  load();
  loadWork();
});
watch(() => props.query.only, (now) => (only.value = now === "1"));
watch(said, (now) => now && only.value && !now.only && (only.value = false));
watch(() => props.query.view, (now) => now && (view.value = now));
watch(() => said.value?.modified, (now, before) => now && before && now !== before && record.reload());
watch(record.record, () => said.value && report());

const taskView = computed(() => ["tasks", "board", "timeline"].includes(view.value));
const taskSpot = usePlace("oneproject.tasks", () => {
  if (!taskView.value || !work.value || !said.value) return null;
  const today = new Date().toISOString().slice(0, 10);
  const open = work.value.tasks.filter((one) => !["Completed", "Cancelled", "Template"].includes(one.status));
  return {
    project: { name: said.value.name, title: said.value.title },
    tasks: {
      view: view.value,
      count: work.value.tasks.length,
      open: open.length,
      late: open.filter((one) => one.exp_end_date && one.exp_end_date < today).length,
    },
  };
});
const LAYOUTS = [
  { value: "tasks", label: __("Table"), icon: "lucide-table" },
  { value: "board", label: __("Board"), icon: "lucide-kanban" },
  { value: "timeline", label: __("Timeline"), icon: "lucide-chart-gantt" },
];
const allowed = (key) => said.value?.views.includes(key);
const VIEWS = computed(() =>
  [
    { key: "overview", label: __("Overview"), icon: "lucide-layout-dashboard" },
    { key: "tasks", label: __("Tasks"), icon: "lucide-list-checks", count: count.value || null },
    allowed("time") && { key: "time", label: __("Timesheet"), icon: "lucide-clock" },
    allowed("money") && { key: "money", label: __("Money"), icon: "lucide-wallet" },
    allowed("invoices") && { key: "invoices", label: __("Invoices"), icon: "lucide-receipt" },
    allowed("suppliers") && { key: "suppliers", label: __("Suppliers"), icon: "lucide-truck", count: said.value.money.suppliers.length || null },
    allowed("team") && { key: "team", label: __("Team"), icon: "lucide-users" },
    { key: "files", label: __("Files"), icon: "lucide-paperclip", count: fileCount.value || null },
    { key: "activity", label: __("Activity"), icon: "lucide-activity" },
  ].filter(Boolean)
);
const layout = ref(["board", "timeline"].includes(props.query.view) ? props.query.view : "tasks");
watch(view, (now) => taskView.value && (layout.value = now));
const tab = computed({
  get: () => (taskView.value ? "tasks" : view.value),
  set: (now) => (view.value = now === "tasks" ? layout.value : now),
});
const tree = computed(() => (work.value?.groups || []).map((one) => one.key));

watch(VIEWS, (now) => said.value && !now.some((one) => one.key === tab.value) && (view.value = "overview"));

const GROUPS = () => ({ project: __("Project"), status: __("Status"), owner: __("Assigned To"), due: __("Expected End Date") });
const groupLabel = computed(() => GROUPS()[groupBy.value]);
const groupChoices = computed(() => Object.entries(GROUPS()).map(([key, label]) => ({ label, selected: key === groupBy.value, onClick: () => (groupBy.value = key) })));
const shown = computed(() => (work.value ? visible(work.value, { search: search.value, showDone: showDone.value }) : []));
const groups = computed(() => (work.value ? groupTasks(work.value, shown.value, groupBy.value) : []));
const team = computed(() => [...new Set([...(said.value?.team || []).map((one) => one.user), ...Object.keys(work.value?.people || {})])]);
function open(task) {
  opened.value = find(task) || null;
}
const views = ref(null);
const room = ref(0);
function makeRoom() {
  const box = views.value?.getBoundingClientRect();
  const panel = 36 * parseFloat(getComputedStyle(document.documentElement).fontSize);
  room.value = opened.value && box && viewWidth() >= 1280 ? Math.max(0, box.right + room.value - (viewWidth() - panel) + 16) : 0;
}
watch(() => Boolean(opened.value), makeRoom);
onBeforeUnmount(onResize(makeRoom));
watch(work, () => opened.value && (opened.value = find(opened.value.name) || null));

async function add(project, subject, extra) {
  await addTask(project || name.value, subject, extra);
}
function newTask() {
  desk().task.new({ values: { project: name.value }, projects: tree.value.length ? tree.value : null, done: loadWork });
}
async function changeProject(fieldname, value) {
  if (fieldname === "status") return changeStatus(value);
  if (fieldname === "project_name") said.value.title = value;
  else said.value[fieldname === "one_health" ? "health" : fieldname] = value;
  await setValue("Project", name.value, fieldname, value);
  load();
}

async function changeStatus(value) {
  const project = name.value;
  const set = (close) => call("onedesk.one_project.status.change", { project, status: value, close: close ? 1 : 0 }).finally(load);
  if (value !== "Completed" && value !== "Cancelled") return set(false);
  const open = await call("onedesk.one_project.status.ask", { project });
  if (!open.tasks && !open.projects) return set(false);
  const parts = [
    open.tasks && (open.tasks === 1 ? __("1 open task") : __("{0} open tasks", [open.tasks])),
    open.projects && (open.projects === 1 ? __("1 open sub-project") : __("{0} open sub-projects", [open.projects])),
  ].filter(Boolean);
  const title = escape(said.value.title);
  confirm(
    value === "Completed" ? __("{0} still has {1}. Complete them too?", [title, andList(parts)]) : __("{0} still has {1}. Cancel them too?", [title, andList(parts)]),
    () => set(true)
  );
}

const templates = computed(() => {
  const s = said.value;
  if (!s) return [];
  return [
    can("create", "Task") && can("read", "Project Template") && { label: __("Add from Template"), icon: "lucide-copy-plus", onClick: () => desk().project.add_template(s.name, loadWork) },
    can("create", "Project Template") && { label: __("Save as Template"), icon: "lucide-save", onClick: () => desk().project.save_as(frm()) },
  ].filter(Boolean);
});
const frm = () => ({ doctype: "Project", doc: { name: said.value.name, project_name: said.value.title, customer: said.value.customer }, reload_doc: load });
const desk = onedesk;

function report() {
  const s = said.value;
  props.onTitle?.({ title: s.title, between: (s.above || []).map((one) => ({ label: one.title, route: projectRoute(one.name) })), after: scopeCrumb(s) });
  props.onStatus?.(null);
  extended(s);
  props.onActions?.([...actions(s), ...verbs, ...record.menu({ gone: () => go("/desk/project") })]);
}

const projectRoute = (project) => `/desk/project/${encodeURIComponent(project)}`;
function scopeCrumb(s) {
  if (!s.below?.length) return [];
  const menu = () => [
    {
      group: __("Show"),
      hide_label: true,
      options: [
        { label: __("All Work"), icon: "layers", selected: !only.value, onclick: () => (only.value = false) },
        { label: __("Main", null, "Project"), icon: "folder", selected: only.value, onclick: () => (only.value = true) },
      ],
    },
    { group: __("Sub-projects"), options: s.below.map((one) => ({ label: one.title, icon: "folder-tree", onclick: () => go(projectRoute(one.name)) })) },
  ];
  return [{ label: only.value ? __("Main", null, "Project") : __("All Work"), menu }];
}

const placed = reactive({ notes: [], actions: [] });
let verbs = [];
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  const doc = record.record.value?.doc;
  if (!places || !doc) return;
  const key = `${s.name}/${doc.modified}/${s.modified}`;
  if (drawn === key) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  verbs = [];
  const lend = () => ({
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
  if (places.listening("oneproject.project")) {
    const project = {
      name: s.name,
      title: s.title,
      kind: s.kind,
      status: s.status,
      health: s.health,
      customer: s.customer,
      currency: s.currency,
      starts: s.starts,
      ends: s.ends,
      percent_complete: s.percent_complete,
      only_main: !!only.value,
    };
    places.emit("oneproject.project", { project }, lend());
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
      "Project"
    );
    verbs = said;
  }
}

function actions(s) {
  const list = [];
  const main = mainAction(s);
  if (main) list.push({ ...main, primary: true });
  if (s.can_write) list.push({ label: __("Ask for Updates"), onClick: () => desk().project.ask_updates(s.name, load) });
  if (s.can_write) list.push({ label: __("Group Under New Project"), onClick: () => desk().project.group(frm()) });
  return list;
}

function mainAction(s) {
  if (s.kind === "Fixed Price" && !s.contract && s.quotation?.count === 1 && can("create", "Sales Order"))
    return { key: "order", label: __("Make Order"), onClick: () => desk().project.order_quote(s.quotation) };
  if (s.kind === "Fixed Price" && s.contract && can("create", "Sales Invoice"))
    return { key: "bill", label: __("Bill Progress"), onClick: () => desk().project.bill_progress(s.orders, s.contract, s.currency, s.overview?.billing?.billable?.share) };
  if (s.kind === "Time and Materials" && s.customer && can("create", "Sales Invoice"))
    return { key: "invoice_time", label: __("Invoice Time"), onClick: () => desk().project.invoice_time(frm()) };
  if (s.kind === "Retainer" && s.customer && can("create", "Sales Invoice"))
    return { key: "invoice_month", label: __("Invoice Month"), onClick: () => desk().project.invoice_month(frm()) };
  return { key: "post", label: __("Post Update"), onClick: writeUpdate };
}

const writing = ref(false);
function writeUpdate() {
  view.value = "overview";
  writing.value = true;
  setTimeout(() => (writing.value = false), 2000);
}
</script>
