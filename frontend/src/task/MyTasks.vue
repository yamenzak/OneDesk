<template>
  <!-- OneTask's page (one_task/page/my_tasks): its column, then the open
       view's tasks in one list, grouped by when each is due
       (one_task/mine.py, read as the reader).
       Modelled on Asana's My Tasks and Todoist's Upcoming: Overdue, the next
       seven days and Later, each task ticked off in place, a timer on it. -->
  <div class="flex">
    <!-- The column stays in sight while the list scrolls. -->
    <div class="sticky top-12 h-[calc(100svh-3rem-var(--one-bar-offset))] shrink-0">
      <Sidebar :aria-label="__('Views')" width="14rem" class="border-e border-outline-gray-1 px-2 py-3">
        <Button variant="solid" icon-left="lucide-plus" class="mb-3 w-full" :label="__('Add Task')" @click="newDoc('Task')" />
        <SidebarItem v-for="one in VIEWS" :key="one.key" :label="one.label" :icon="one.icon" :active="view === one.key" @click="open(one.key)">
          <template #suffix>
            <Badge v-if="one.key === 'mine' && counts.late" class="me-1" :label="String(counts.late)" theme="red" size="sm" :title="__('Overdue')" />
            <span v-if="counts[one.key]" class="pe-2 text-sm tabular-nums text-ink-gray-5">{{ counts[one.key] }}</span>
          </template>
        </SidebarItem>
        <div class="mt-auto border-t border-outline-gray-1 pt-2">
          <SidebarItem :label="__('All Tasks')" icon="lucide-circle-check" @click="go('/desk/task?is_template=0')" />
          <!-- As the rail has it (sidebar/onetask), for whoever may open it. -->
          <SidebarSection v-if="delays" :label="__('Reports')" collapsible>
            <SidebarItem :label="__('Task Delays')" icon="lucide-chart-line" @click="go(DELAYS)" />
          </SidebarSection>
          <SidebarSection v-if="can('read', 'Task Type')" v-model:collapsed="setupClosed" :label="__('Setup')" collapsible>
            <SidebarItem :label="__('Task Type')" icon="lucide-tag" @click="go('/desk/task-type')" />
          </SidebarSection>
        </div>
      </Sidebar>
    </div>

    <main class="mx-auto w-full min-w-0 max-w-4xl px-4 pb-16 pt-5 sm:px-8">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ shown.label }}</h1>
      <!-- A task of one's own, in no project: its name, and when it is due. -->
      <div class="mt-4 flex gap-2">
        <TextInput v-model="subject" class="min-w-0 flex-1" :placeholder="__('Add a task')" :maxlength="140" :disabled="adding" :aria-label="__('Add a task')" @keydown.enter.prevent="add" />
        <DatePicker v-model="due" class="w-32 shrink-0 sm:w-40" :format="dateFormat()" :placeholder="__('Expected End Date')" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />

      <Loading v-if="!groups" />
      <p v-else-if="!groups.length" class="py-10 text-center text-base text-ink-gray-5">{{ shown.empty }}</p>
      <List v-else :columns="columns" divider="full" class="mt-4 list-gap-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Task") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Project or About") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Expected End Date") }}</ListHeaderCell>
          <ListHeaderCell v-if="times" />
        </ListHeader>
        <ListGroup v-for="group in groups" :key="group.key">
          <template #label>
            <span :class="group.key === 'overdue' ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ group.label }}</span>
            <span class="ms-2 tabular-nums">{{ group.tasks.length }}</span>
          </template>
          <ListRow v-for="task in group.tasks" :key="task.name" class="py-2">
            <ListCell class="min-w-0 gap-3">
              <Checkbox :model-value="ticked.has(task.name)" :aria-label="__('Complete {0}', [task.subject])" :disabled="busy.has(task.name)" @update:model-value="(on) => tick(task, on)" />
              <div class="flex min-w-0 flex-col gap-0.5">
                <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                  <button class="text-start text-base text-ink-gray-8 hover:underline max-md:line-clamp-2 md:truncate" :class="ticked.has(task.name) && 'text-ink-gray-4 line-through'" @click="go(`/desk/task/${encodeURIComponent(task.name)}`)">{{ task.subject }}</button>
                  <Badge v-if="PRESSING[task.priority]" :label="__(task.priority)" :theme="PRESSING[task.priority]" size="sm" />
                  <Badge v-if="task.status !== 'Open'" :label="__(task.status)" :theme="TASK_STATUS[task.status] || 'gray'" size="sm" />
                  <Badge v-if="task.waiting" :label="__('Waiting')" theme="amber" size="sm" :title="__('Waiting on {0} other tasks', [task.waiting])" />
                  <Badge v-if="task.is_milestone" :label="__('Milestone')" theme="violet" size="sm" />
                  <Badge v-if="running?.task === task.name" :label="__('Since {0}', [clock(running.since)])" theme="blue" size="sm" />
                </div>
                <!-- On a phone the project goes under the name. -->
                <button v-if="where(task)" class="truncate text-start text-sm text-ink-gray-5 md:hidden" :disabled="!where(task).route" @click="go(where(task).route)">{{ where(task).label }}</button>
              </div>
            </ListCell>
            <ListCell class="min-w-0 max-md:hidden">
              <button v-if="where(task)" class="truncate text-start text-base text-ink-gray-7 enabled:hover:underline" :title="where(task).kind" :disabled="!where(task).route" @click="go(where(task).route)">{{ where(task).label }}</button>
            </ListCell>
            <ListCell class="text-base tabular-nums max-md:text-sm" :class="group.key === 'overdue' ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ day(task.due, group.key) }}</ListCell>
            <ListCell v-if="times" class="justify-end">
              <Button variant="ghost" size="sm" :icon="running?.task === task.name ? 'lucide-square' : 'lucide-play'" :aria-label="running?.task === task.name ? __('Stop Timer') : __('Start Timer')" :title="running?.task === task.name ? __('Stop Timer') : __('Start Timer')" @click="time(task)" />
            </ListCell>
          </ListRow>
        </ListGroup>
      </List>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { Badge, Button, Checkbox, DatePicker, Sidebar, SidebarItem, SidebarSection, TextInput } from "frappe-ui";
import { List, ListCell, ListGroup, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { Loading, PlaceSpot, __, ago, call, can, canReport, clock, date, dateFormat, followList, go, insert, listen, newDoc, onedesk, setQuery, setValue, weekday } from "../kit";
import { TASK_STATUS } from "../project/colors";
import { usePlace } from "../project/place";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
});

// The views, in the column's order. The key is `?section=`, which is how
// OneAI knows which is open (oneai.js `where`).
const VIEWS = [
  { key: "mine", label: __("My Tasks"), icon: "lucide-list-checks", empty: __("No tasks assigned to you") },
  { key: "inbox", label: __("Inbox"), icon: "lucide-inbox", empty: __("No tasks in Inbox") },
];
const PRESSING = { Urgent: "red", High: "amber" };
// The groups in their order (one_task/mine.py GROUPS).
const WHEN = ["overdue", "today", "tomorrow", "week", "later", "none"];

const view = ref(VIEWS.some((one) => one.key === props.query.section) ? props.query.section : "mine");
const shown = computed(() => VIEWS.find((one) => one.key === view.value));
const groups = ref(null);
const counts = ref({});
const running = ref(null);
const setupClosed = ref(true);
// ERPNext's Delayed Tasks Summary, under the rail's name for it.
const DELAYS = "/desk/query-report/Delayed Tasks Summary";
const delays = canReport("Delayed Tasks Summary");
// Whoever may keep a timesheet may time a task (one_task/timer.py).
const times = can("create", "Timesheet");
const columns = computed(() => ({
  base: ["minmax(0,1fr)", "5.5rem", ...(times ? ["2rem"] : [])],
  md: ["minmax(0,1fr)", "minmax(0,14rem)", "7rem", ...(times ? ["2rem"] : [])],
}));

async function load() {
  const [now, many, timing] = await Promise.all([
    call("onedesk.one_task.mine.tasks", { view: view.value }),
    call("onedesk.one_task.mine.counts"),
    times ? call("onedesk.one_task.timer.running") : null,
  ]);
  groups.value = kept(now);
  counts.value = many || {};
  running.value = timing;
}

// A task ticked here stays in its group, struck through, until the view is
// left, though the list drawn again no longer has it.
function kept(now) {
  const was = Object.fromEntries((groups.value || []).flatMap((group) => group.tasks.map((one) => [one.name, [group, one]])));
  for (const name of ticked) {
    if (!was[name] || now.some((group) => group.tasks.some((one) => one.name === name))) continue;
    const [group, task] = was[name];
    let into = now.find((one) => one.key === group.key);
    if (!into) {
      into = { ...group, tasks: [] };
      now.push(into);
    }
    into.tasks.push(task);
  }
  return now.sort((a, b) => WHEN.indexOf(a.key) - WHEN.indexOf(b.key));
}

function open(key) {
  if (key === view.value) return;
  view.value = key;
  groups.value = null;
  ticked.clear();
  setQuery("section", key === "mine" ? null : key);
  load();
}
watch(() => props.query.section, (now) => open(VIEWS.some((one) => one.key === now) ? now : "mine"));

// The project a task is in, as a path through sub-projects, or the
// onboarding it is a step of (one_task/mine.py `place`), or, for one in no
// project, the record it is about (a task OneIntake made about a supplier).
function where(task) {
  if (task.place) return { ...task.place, kind: __(task.place.kind) };
  if (task.about_title)
    return {
      label: task.about_title,
      route: `/desk/${task.one_about_doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(task.one_about)}`,
      kind: __(task.one_about_doctype),
    };
  return null;
}

// Late, how long ago it was due; in the next week, its weekday; anything
// else its date. Today and tomorrow are already the group's name.
function day(due, group) {
  if (!due || group === "today" || group === "tomorrow") return "";
  if (group === "overdue") return ago(due);
  if (group === "week") return weekday(due);
  return date(due);
}

// Ticked stays on the list, struck through (`kept`), so a tick made by
// mistake is undone where it was made. Through frappe's own save, so ERPNext
// closes the task's assignments as it does from the form.
const ticked = reactive(new Set());
const busy = reactive(new Set());
let quietUntil = 0;
const quiet = () => (quietUntil = Date.now() + 1500);
async function tick(task, on) {
  busy.add(task.name);
  try {
    await setValue("Task", task.name, "status", on ? "Completed" : "Open");
    on ? ticked.add(task.name) : ticked.delete(task.name);
  } finally {
    busy.delete(task.name);
    quiet();
  }
}

const subject = ref("");
const due = ref("");
const adding = ref(false);
async function add() {
  const said = subject.value.trim();
  if (!said) return;
  adding.value = true;
  try {
    await insert({ doctype: "Task", subject: said, exp_end_date: due.value || null });
    subject.value = "";
    due.value = "";
    await load();
  } finally {
    adding.value = false;
    quiet();
  }
}

// One timer runs at a time; starting this one pauses whichever was running.
async function time(task) {
  if (running.value?.task === task.name) {
    onedesk().task_timer?.stopped?.(await call("onedesk.one_task.timer.stop"));
    running.value = null;
  } else running.value = await call("onedesk.one_task.timer.start", { task: task.name });
}

// The workspace's extensions on OneTask (one_studio/places.py), told which
// view is open and what it lists.
const placed = usePlace(
  "onetask.listed",
  computed(() =>
    groups.value
      ? {
          view: view.value,
          groups: groups.value.map((group) => ({
            key: group.key,
            label: group.label,
            tasks: group.tasks.map((one) => ({
              name: one.name,
              subject: one.subject,
              priority: one.priority,
              due: one.due,
              project: one.project,
              project_title: one.project_title,
              is_milestone: !!one.is_milestone,
            })),
          })),
        }
      : null
  )
);

// A task given, saved or ticked elsewhere draws the list again, a moment
// after the last change. A change made here is not heard as somebody else's,
// or a tick would take its row away at once.
let soon = null;
const again = () => {
  if (Date.now() < quietUntil) return;
  clearTimeout(soon);
  soon = setTimeout(load, 800);
};
let stop = [];
onMounted(() => {
  load();
  // A timer paused, resumed or stopped anywhere, the rail's Timers included.
  const timed = async () => (running.value = times ? await call("onedesk.one_task.timer.running") : null);
  stop = [followList("Task", again), followList("ToDo", again), listen("one_timers", timed)];
});
onBeforeUnmount(() => {
  clearTimeout(soon);
  stop.forEach((one) => one());
});
</script>
