<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <!-- The views, as monday's and Asana's: each opens in place. On a
           desktop they are a column beside the project, where OneProject's
           sidebar was. -->
      <div class="lg:grid lg:grid-cols-[11rem_minmax(0,1fr)] lg:gap-8">
        <nav class="max-lg:hidden">
          <div class="sticky top-[calc(var(--page-head-height,48px)+1.5rem)] z-[5] pt-6">
            <Tabs v-model="tab" vertical>
              <TabList variant="ghost" class="w-full">
                <TabTrigger v-for="one in VIEWS" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
                  <template v-if="one.count" #suffix><span class="ms-auto ps-2 text-sm text-ink-gray-5">{{ one.count }}</span></template>
                </TabTrigger>
              </TabList>
            </Tabs>
          </div>
        </nav>
        <div class="min-w-0">
          <Header :said="said" @change="changeProject" @media="load" @view="(now) => (view = now)" @whole="only = false" />
          <!-- The task views' toolbar, and below a desktop's width the views as a
               tab bar that scrolls sideways, as an app's does. It sticks under
               desk's page head, never over it (the head is z-index 6). -->
          <div class="sticky top-[var(--page-head-height,48px)] z-[5] mt-4 flex flex-wrap items-center gap-x-2 border-b border-outline-gray-2 bg-surface-base" :class="{ 'lg:hidden': !taskView }">
            <Tabs v-model="tab" class="max-w-full overflow-x-auto [scrollbar-width:none] lg:hidden">
              <TabList class="border-0">
                <TabTrigger v-for="one in VIEWS" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
                  <template v-if="one.count" #suffix><span class="ms-1 text-sm text-ink-gray-5">{{ one.count }}</span></template>
                </TabTrigger>
              </TabList>
            </Tabs>
            <div v-if="taskView" class="ms-auto flex max-w-full flex-wrap items-center gap-2 py-2 max-md:w-full">
              <TabButtons v-model="view" :options="LAYOUTS" />
              <TextInput v-model="search" size="sm" class="w-44 max-md:order-last max-md:w-full" :placeholder="__('Search')">
                <template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
              </TextInput>
              <Dropdown v-if="view === 'tasks' || view === 'timeline'" :options="groupChoices">
                <template #trigger><Button size="sm" icon-left="lucide-rows-3" :label="__('Group by {0}', [groupLabel])" /></template>
              </Dropdown>
              <Button size="sm" :variant="showDone ? 'subtle' : 'ghost'" icon-left="lucide-circle-check" :label="__('Done')" @click="showDone = !showDone" />
              <Button v-if="work?.can_create" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Task')" @click="newTask" />
            </div>
          </div>

          <Overview v-if="view === 'overview'" :said="said" :writing="writing" @changed="load" @view="(now) => (view = now)" @main="only = true" />
          <template v-else-if="taskView">
            <Loading v-if="!work" />
            <Tasks v-else-if="view === 'tasks'" :work="work" :groups="groups" :team="team" :can-write="work.can_write" @open="open" @set="set" @give="give" @take="take" @add="add" />
            <Board v-else-if="view === 'board'" :work="work" :tasks="shown" :show-done="showDone" :can-write="work.can_write" @open="open" @set="set" />
            <Timeline v-else :work="work" :groups="groups" @open="open" />
          </template>
          <Time v-else-if="view === 'time'" :project-name="said.name" :customer="said.customer" :title="said.title" :tree="tree" />
          <Money v-else-if="view === 'money'" :said="said" @changed="load" />
          <Invoices v-else-if="view === 'invoices'" :project-name="said.name" :project-title="said.title" :kind="said.kind" :customer="said.customer" :currency="said.currency" />
          <Team v-else-if="view === 'team'" :project-name="said.name" :modified="said.modified" @changed="load" />
          <Suppliers v-else-if="view === 'suppliers'" :said="said" />
          <Files v-else-if="view === 'files'" :project="said.name" :work="work" @count="(n) => (fileCount = n)" />
          <ProjectActivity v-else-if="view === 'activity'" :key="said.name" :project="said.name" :modified="said.modified" @task="open" />
        </div>
      </div>

      <TaskPanel :task="opened" :work="work || EMPTY" :team="team" :can-write="work?.can_write" @close="opened = null" @set="set" @give="give" @take="take" @open="open" @add="add" @changed="loadWork" />
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
import { Button, Dropdown, TabButtons, TabList, Tabs, TabTrigger, TextInput } from "frappe-ui";

import { Loading, Page, __, andList, call, can, confirm, escape, follow, go, listen, newDoc, onedesk, setQuery, setValue } from "../kit";
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
import { useWork } from "./useWork";

// The timeline brings frappe-ui's editor, so it loads when first shown.
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
// Only the project's own work, its Main, and not what is under it: kept in
// the address so it can be shared and survives a reload.
const only = ref(props.query.only === "1");
provideOnly(only);

const { work, load: loadWork, set, add: addTask, give, take, find, count } = useWork(name, only);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_project.view.said", { project: asked, ...onlyArg(only) });
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
    stop = [
      follow("Project", now, load),
      listen("one_project_money", (data) => data.project === now && load()),
      listen("one_project_media", (data) => data.project === now && load()),
    ];
    load();
    loadWork();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop.forEach((one) => one()));
watch(view, (now) => setQuery("view", now === "overview" ? null : now));
watch(only, (now) => {
  setQuery("only", now ? "1" : null);
  said.value = null;
  load();
  loadWork();
});
watch(() => props.query.only, (now) => (only.value = now === "1"));
// A project with nothing under it has no Main to show on its own.
watch(said, (now) => now && only.value && !now.only && (only.value = false));
watch(() => props.query.view, (now) => now && (view.value = now));

const taskView = computed(() => ["tasks", "board", "timeline"].includes(view.value));
// The views in the bar. Board and Timeline are the tasks laid out another way,
// as monday's views of a board are, so they sit under Tasks and its switch.
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
    // Each of these only for whoever may see it (view.py `views`).
    allowed("time") && { key: "time", label: __("Time"), icon: "lucide-clock" },
    allowed("money") && { key: "money", label: __("Money"), icon: "lucide-wallet" },
    allowed("invoices") && { key: "invoices", label: __("Invoices"), icon: "lucide-receipt" },
    allowed("suppliers") && { key: "suppliers", label: __("Suppliers"), icon: "lucide-truck", count: said.value.money.suppliers.length || null },
    allowed("team") && { key: "team", label: __("Team"), icon: "lucide-users" },
    { key: "files", label: __("Files"), icon: "lucide-paperclip", count: fileCount.value || null },
    { key: "activity", label: __("Activity"), icon: "lucide-activity" },
  ].filter(Boolean)
);
// The tab shown as chosen: Tasks for any of its layouts, which it reopens on.
const layout = ref(["board", "timeline"].includes(props.query.view) ? props.query.view : "tasks");
watch(view, (now) => taskView.value && (layout.value = now));
const tab = computed({
  get: () => (taskView.value ? "tasks" : view.value),
  set: (now) => (view.value = now === "tasks" ? layout.value : now),
});
const tree = computed(() => (work.value?.groups || []).map((one) => one.key));

// A view the reader may not see (Money, Suppliers) opens Overview instead.
watch(VIEWS, (now) => said.value && !now.some((one) => one.key === tab.value) && (view.value = "overview"));

const GROUPS = () => ({ project: __("Project"), status: __("Status"), owner: __("Owner"), due: __("Due Date") });
const groupLabel = computed(() => GROUPS()[groupBy.value]);
const groupChoices = computed(() => Object.entries(GROUPS()).map(([key, label]) => ({ label, selected: key === groupBy.value, onClick: () => (groupBy.value = key) })));
const shown = computed(() => (work.value ? visible(work.value, { search: search.value, showDone: showDone.value }) : []));
const groups = computed(() => (work.value ? groupTasks(work.value, shown.value, groupBy.value) : []));
const team = computed(() => [...new Set([...(said.value?.team || []).map((one) => one.user), ...Object.keys(work.value?.people || {})])]);
function open(task) {
  opened.value = find(task) || null;
}
watch(work, () => opened.value && (opened.value = find(opened.value.name) || null));

async function add(project, subject, extra) {
  await addTask(project || name.value, subject, extra);
}
function newTask() {
  newDoc("Task", { project: name.value });
}
async function changeProject(fieldname, value) {
  if (fieldname === "status") return changeStatus(value);
  if (fieldname === "project_name") said.value.title = value;
  else said.value[fieldname === "one_health" ? "health" : fieldname] = value;
  await setValue("Project", name.value, fieldname, value);
  load();
}

// Completing or cancelling a project closes what's still open in it, on the
// reader's say-so; ERPNext would set it back to Open otherwise
// (one_project/status.py).
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

// The project as desk's shared actions take it (project_actions.js).
const frm = () => ({ doctype: "Project", doc: { name: said.value.name, project_name: said.value.title, customer: said.value.customer }, reload_doc: load });
const desk = onedesk;

function report() {
  const s = said.value;
  props.onTitle?.({ title: s.title, between: (s.above || []).map((one) => ({ label: one.title, route: `/desk/project/${encodeURIComponent(one.name)}` })) });
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
  if (main?.key !== "post") list.push({ label: __("Post Update"), onClick: writeUpdate });
  if (s.can_write) list.push({ label: __("Ask for Updates"), onClick: () => desk().project.ask_updates(s.name, load) });
  // A Fixed Price project is quoted, and quoted again, until it has its
  // contract; what is quoted after is extra work, ordered as a sub-project.
  if (s.customer && can("create", "Quotation")) {
    if (s.kind === "Fixed Price" && !s.contract) list.push({ label: __("New Quotation"), onClick: () => newDoc("Quotation", { project: s.name, quotation_to: "Customer", party_name: s.customer }) });
    else list.push({ label: __("Quote Extra Work"), onClick: () => newDoc("Quotation", { project: s.name, one_extra_work: 1, quotation_to: "Customer", party_name: s.customer }) });
  }
  // What the work uses: stock taken out for it, and what the team paid
  // themselves, each naming the project (one_project/money.py).
  if (can("create", "Stock Entry")) list.push({ label: __("Issue Stock"), onClick: () => newDoc("Stock Entry", { stock_entry_type: "Material Issue", purpose: "Material Issue", project: s.name }) });
  if (can("create", "Expense Claim")) list.push({ label: __("New Expense Claim"), onClick: () => newDoc("Expense Claim", { project: s.name }) });
  if (s.can_write && can("create", "Project")) list.push({ label: __("Add Sub-project"), onClick: () => newDoc("Project", { one_parent: s.name, customer: s.customer }) });
  if (s.can_write) list.push({ label: __("Group Under New Project"), onClick: () => desk().project.group(frm()) });
  if (can("create", "Task") && can("read", "Project Template")) list.push({ label: __("Add from Template"), onClick: () => desk().project.add_template(s.name, loadWork) });
  if (can("create", "Project Template")) list.push({ label: __("Save as Template"), onClick: () => desk().project.save_as(frm()) });
  if (can("read", "Task")) list.push({ label: __("Open Task Board"), onClick: () => desk().project.board(frm()) });
  return list;
}

function mainAction(s) {
  // While it's quoted and not ordered, the next step is the customer's order.
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

// An update is written in the line under Updates on the Overview, which
// takes the cursor when `writing` is set (Updates.vue).
const writing = ref(false);
function writeUpdate() {
  view.value = "overview";
  writing.value = true;
  setTimeout(() => (writing.value = false), 2000);
}
</script>
