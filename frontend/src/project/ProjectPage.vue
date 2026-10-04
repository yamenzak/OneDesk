<template>
  <Page>
    <Loading v-if="!said" />
    <template v-else>
      <Header :said="said" :progress="progress" @change="changeProject" />

      <!-- The views, as monday's and Asana's: each opens in place, and the
           task views share one toolbar. -->
      <div class="sticky top-0 z-10 mt-4 flex flex-wrap items-center gap-x-2 border-b border-outline-gray-2 bg-surface-base">
        <Tabs v-model="view">
          <TabList class="border-0">
            <TabTrigger v-for="one in VIEWS" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
              <template v-if="one.count" #suffix><span class="ms-1 text-sm text-ink-gray-5">{{ one.count }}</span></template>
            </TabTrigger>
          </TabList>
        </Tabs>
        <div v-if="taskView" class="ms-auto flex items-center gap-2 py-2">
          <TextInput v-model="search" size="sm" class="w-44" :placeholder="__('Search')">
            <template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
          </TextInput>
          <Dropdown v-if="view === 'tasks' || view === 'timeline'" :options="groupChoices">
            <template #trigger><Button size="sm" icon-left="lucide-rows-3" :label="__('Group by {0}', [groupLabel])" /></template>
          </Dropdown>
          <Button size="sm" :variant="showDone ? 'subtle' : 'ghost'" icon-left="lucide-circle-check" :label="__('Done')" @click="showDone = !showDone" />
          <Button v-if="work?.can_create" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Task')" @click="newTask" />
        </div>
      </div>

      <Overview v-if="view === 'overview'" :said="said" @changed="load" />
      <template v-else-if="taskView">
        <Loading v-if="!work" />
        <Tasks v-else-if="view === 'tasks'" :work="work" :groups="groups" :team="team" :can-write="work.can_write" @open="open" @set="set" @give="give" @take="take" @add="add" />
        <Board v-else-if="view === 'board'" :work="work" :tasks="shown" :show-done="showDone" :can-write="work.can_write" @open="open" @set="set" />
        <Timeline v-else :work="work" :groups="groups" @open="open" />
      </template>
      <Money v-else-if="view === 'money'" :said="said" @changed="load" />
      <Suppliers v-else-if="view === 'suppliers'" :said="said" />
      <Files v-else-if="view === 'files'" :project="said.name" :work="work" @count="(n) => (fileCount = n)" />
      <Activity v-else-if="view === 'activity'" :key="said.name" doctype="Project" :name="said.name" />

      <TaskPanel :task="opened" :work="work || EMPTY" :team="team" :can-write="work?.can_write" @close="opened = null" @set="set" @give="give" @take="take" />
    </template>
  </Page>
</template>

<script setup>
// A project's workspace (docs/PROJECT-PAGE.md): its head, then its views,
// each opening in place, as monday and Asana present a project. What it reads
// is one_project/view.py's `said` and `work`; what it changes it changes as
// desk does. Desk's own page head above it carries the main action and the
// rest (onedesk.island_page), from what `report` says.
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue";
import { Button, Dropdown, TabList, Tabs, TabTrigger, TextInput } from "frappe-ui";

import { Loading, Page, __, call, can, follow, go, listen, newDoc, onedesk, setQuery, setValue } from "../kit";
import Board from "./Board.vue";
import Files from "./Files.vue";
import Header from "./Header.vue";
import Money from "./Money.vue";
import Overview from "./Overview.vue";
import Suppliers from "./Suppliers.vue";
import TaskPanel from "./TaskPanel.vue";
import Tasks from "./Tasks.vue";
import Timeline from "./Timeline.vue";
import { groupTasks, visible } from "./group";
import { useWork } from "./useWork";

// The timeline brings frappe-ui's editor, so it loads when first shown.
const Activity = defineAsyncComponent(() => import("./Activity.vue"));

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

const { work, load: loadWork, set, add: addTask, give, take, find, count } = useWork(name);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_project.view.said", { project: asked });
  if (asked !== name.value) return;
  said.value = got;
  report();
}

let stop = [];
watch(
  name,
  (now) => {
    stop.forEach((one) => one());
    said.value = null;
    opened.value = null;
    if (!now) return;
    stop = [follow("Project", now, load), listen("one_project_money", (data) => data.project === now && load())];
    load();
    loadWork();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop.forEach((one) => one()));
watch(view, (now) => setQuery("view", now === "overview" ? null : now));
watch(() => props.query.view, (now) => now && (view.value = now));

const taskView = computed(() => ["tasks", "board", "timeline"].includes(view.value));
const VIEWS = computed(() => [
  { key: "overview", label: __("Overview"), icon: "lucide-layout-dashboard" },
  { key: "tasks", label: __("Tasks"), icon: "lucide-list-checks", count: count.value || null },
  { key: "board", label: __("Board"), icon: "lucide-kanban" },
  { key: "timeline", label: __("Timeline"), icon: "lucide-chart-gantt" },
  // Money and Suppliers only for whoever may see them, and Suppliers where
  // there are subcontracts or a Fixed Price project expects them (view.py).
  ...(said.value?.views.includes("money") ? [{ key: "money", label: __("Money"), icon: "lucide-wallet" }] : []),
  ...(said.value?.views.includes("suppliers")
    ? [{ key: "suppliers", label: __("Suppliers"), icon: "lucide-truck", count: said.value.money.suppliers.length || null }]
    : []),
  { key: "files", label: __("Files"), icon: "lucide-paperclip", count: fileCount.value || null },
  { key: "activity", label: __("Activity"), icon: "lucide-activity" },
]);

// A view the reader may not see (Money, Suppliers) opens Overview instead.
watch(VIEWS, (now) => said.value && !now.some((one) => one.key === view.value) && (view.value = "overview"));

const GROUPS = () => ({ project: __("Project"), status: __("Status"), owner: __("Owner"), due: __("Due Date") });
const groupLabel = computed(() => GROUPS()[groupBy.value]);
const groupChoices = computed(() => Object.entries(GROUPS()).map(([key, label]) => ({ label, selected: key === groupBy.value, onClick: () => (groupBy.value = key) })));
const shown = computed(() => (work.value ? visible(work.value, { search: search.value, showDone: showDone.value }) : []));
const groups = computed(() => (work.value ? groupTasks(work.value, shown.value, groupBy.value) : []));
const team = computed(() => [...new Set([...(said.value?.team || []).map((one) => one.user), ...Object.keys(work.value?.people || {})])]);
// One figure for how far along it is, the same the Done figure shows.
const progress = computed(() => {
  const done = said.value?.cards?.find((card) => card.key === "done");
  if (done) return done.bar ?? null;
  if (!work.value?.tasks.length) return null;
  const all = work.value.tasks.filter((one) => one.status !== "Cancelled");
  return all.length ? Math.floor((100 * all.filter((one) => one.status === "Completed").length) / all.length) : null;
});

function open(task) {
  opened.value = find(task) || null;
}
watch(work, () => opened.value && (opened.value = find(opened.value.name) || null));

async function add(project, subject) {
  await addTask(project || name.value, subject);
}
function newTask() {
  newDoc("Task", { project: name.value });
}
async function changeProject(fieldname, value) {
  if (fieldname === "project_name") said.value.title = value;
  else said.value[fieldname === "one_health" ? "health" : fieldname] = value;
  await setValue("Project", name.value, fieldname, value);
  load();
}

// The project as desk's shared actions take it (project_actions.js).
const frm = () => ({ doctype: "Project", doc: { name: said.value.name, project_name: said.value.title, customer: said.value.customer }, reload_doc: load });
const desk = onedesk;

function report() {
  const s = said.value;
  props.onTitle?.(s.title);
  props.onStatus?.(null);
  props.onActions?.(actions(s));
}

// What can be done to the project, each only for whoever may do it. The
// views are in the page; the head keeps the kind's main action and the rest.
function actions(s) {
  const list = [];
  const main = mainAction(s);
  if (main) list.push({ ...main, primary: true });
  list.push({ label: __("Edit Details"), onClick: () => go(`/desk/project/${encodeURIComponent(s.name)}?edit=1`) });
  if (main?.key !== "post") list.push({ label: __("Post Update"), onClick: () => desk().project.post(frm()) });
  if (s.customer && can("create", "Quotation"))
    list.push({ label: __("Quote Extra Work"), onClick: () => newDoc("Quotation", { project: s.name, one_extra_work: 1, quotation_to: "Customer", party_name: s.customer }) });
  if (s.can_write) list.push({ label: __("Group Under New Project"), onClick: () => desk().project.group(frm()) });
  if (can("create", "Project Template")) list.push({ label: __("Save as Template"), onClick: () => desk().project.save_as(frm()) });
  if (can("read", "Task")) list.push({ label: __("Open Task Board"), onClick: () => desk().project.board(frm()) });
  return list;
}

function mainAction(s) {
  if (s.kind === "Fixed Price" && s.contract && can("create", "Sales Invoice"))
    return { key: "bill", label: __("Bill Progress"), onClick: () => desk().progress.ask({ doctype: "Sales Order", doc: { name: s.contract } }) };
  if (s.kind === "Time and Materials" && s.customer && can("create", "Sales Invoice"))
    return { key: "invoice_time", label: __("Invoice Time"), onClick: () => desk().project.invoice_time(frm()) };
  return { key: "post", label: __("Post Update"), onClick: () => desk().project.post(frm()) };
}
</script>
