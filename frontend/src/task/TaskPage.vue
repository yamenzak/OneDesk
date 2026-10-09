<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <!-- The task's head: where it stands, what it is called, the one thing
           worth saying, when it runs and how far along it is. Frappe's own
           form sidebar is on the page's right (onedesk.island_page). -->
      <header class="pt-6">
        <div class="flex flex-wrap items-center gap-2">
          <Pill :value="said.status" :options="said.statuses" :colors="TASK_STATUS" :label="__('Status')" :readonly="!said.can_write" @change="(v) => set('status', v)" />
          <Pill :value="said.priority" :options="said.priorities" :colors="PRIORITY" :label="__('Priority')" :readonly="!said.can_write" @change="(v) => set('priority', v)" />
          <Badge v-if="said.is_milestone" :label="__('Milestone')" theme="violet" size="md" />
          <Badge v-if="said.is_template" :label="__('Template')" theme="gray" size="md" />
        </div>
        <Title class="mt-3" :said="{ title: said.subject, can_write: said.can_write }" size="text-3xl lg:text-4xl" field="subject" :label="__('Subject')" @change="set" />
        <p v-if="headline" class="mt-1 text-base" :class="TONE[said.headline.tone]">{{ headline }}</p>
        <dl class="mt-4 flex flex-wrap gap-x-8 gap-y-3 text-base">
          <div class="flex flex-col gap-1">
            <dt class="text-sm text-ink-gray-5">{{ __("Starts") }}</dt>
            <dd class="w-40"><Due :value="day(said.exp_start_date)" done :readonly="!said.can_write" @change="(v) => set('exp_start_date', v)" /></dd>
          </div>
          <div class="flex flex-col gap-1">
            <dt class="text-sm text-ink-gray-5">{{ __("Due") }}</dt>
            <dd class="w-40"><Due :value="day(said.exp_end_date)" :done="DONE.includes(said.status)" :readonly="!said.can_write" @change="(v) => set('exp_end_date', v)" /></dd>
          </div>
          <div class="flex flex-col gap-1">
            <dt class="text-sm text-ink-gray-5">{{ __("Planned") }}</dt>
            <dd class="flex items-center gap-1">
              <TextInput type="number" size="sm" variant="ghost" min="0" step="0.5" class="w-24 tabular-nums" :model-value="said.expected_time || ''" :disabled="!said.can_write" :aria-label="__('Planned Hours')" :placeholder="__('Set Hours')" @change="(e) => set('expected_time', Number(e.target.value) || 0)" />
              <span v-if="said.expected_time" class="text-ink-gray-5">{{ __("h") }}</span>
            </dd>
          </div>
          <div v-if="said.repeat" class="flex flex-col gap-1">
            <dt class="text-sm text-ink-gray-5">{{ __("Repeats") }}</dt>
            <dd class="py-1 text-ink-gray-8">{{ said.repeat.disabled ? __("Stopped") : __(said.repeat.frequency) }}</dd>
          </div>
          <div v-if="said.about_title" class="flex min-w-0 flex-col gap-1">
            <dt class="text-sm text-ink-gray-5">{{ __("About") }}</dt>
            <dd class="truncate py-1"><button :class="LINK" @click="go(`/desk/${slug(said.one_about_doctype)}/${encodeURIComponent(said.one_about)}`)">{{ said.about_title }}</button></dd>
          </div>
        </dl>
        <Figures v-if="figures.length" :figures="figures" :columns="figures.length" boxed class="mt-5" />
      </header>

      <!-- What the workspace's extensions add to the page (one_studio/places.py). -->
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="view" :views="VIEWS" class="mt-5" />

      <div class="pt-4">
        <div v-if="view === 'details'" class="grid gap-8 pb-12 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div class="flex min-w-0 flex-col gap-8">
            <section>
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Description") }}</h3>
                <Button v-if="said.can_write" variant="ghost" size="sm" icon="lucide-pencil" :aria-label="__('Edit Description')" @click="describe" />
              </div>
              <div v-if="said.description" class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.description" />
              <button v-else-if="said.can_write" class="text-base text-ink-gray-5 hover:text-ink-gray-8" @click="describe">{{ __("Add Description") }}</button>
              <p v-else class="text-base text-ink-gray-5">{{ __("No description") }}</p>
            </section>

            <section v-if="said.steps.length || said.can_write">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Checklist") }}</h3>
                <span v-if="said.steps.length" class="text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [doneSteps, said.steps.length]) }}</span>
              </div>
              <div class="flex flex-col gap-1.5">
                <Checkbox v-for="one in said.steps" :key="one.name" :model-value="Boolean(one.done)" :label="one.step" :disabled="!said.can_write" @update:model-value="(v) => tick(one, v)" />
              </div>
              <TextInput v-if="said.can_write" v-model="newStep" size="sm" class="mt-2 max-w-md" :placeholder="__('Add Step')" @keydown.enter="addStep" />
            </section>

            <section v-if="said.sub_tasks.length || said.can_create">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Sub-tasks") }}</h3>
                <span v-if="said.sub_tasks.length" class="text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [doneSubs, said.sub_tasks.length]) }}</span>
              </div>
              <div class="flex flex-col divide-y divide-outline-gray-1">
                <button v-for="one in said.sub_tasks" :key="one.name" class="flex min-w-0 items-center gap-2 py-2 text-start text-base hover:bg-surface-gray-1" @click="go(`/desk/task/${encodeURIComponent(one.name)}`)">
                  <span class="lucide-circle-check size-4 shrink-0" :class="one.status === 'Completed' ? 'text-ink-green-3' : 'text-ink-gray-4'" aria-hidden="true" />
                  <span class="me-auto truncate" :class="one.status === 'Completed' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'">{{ one.subject }}</span>
                  <span v-if="one.exp_end_date" class="shrink-0 text-sm" :class="late(one) ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ date(day(one.exp_end_date)) }}</span>
                  <People :users="one.assigned" :people="said.people" class="shrink-0" />
                </button>
              </div>
              <TextInput v-if="said.can_create" v-model="newSub" size="sm" class="mt-2 max-w-md" :placeholder="__('Add Sub-task')" @keydown.enter="addSub" />
            </section>
          </div>

          <aside class="flex min-w-0 flex-col gap-8">
            <section>
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Depends On") }}</h3>
                <Button v-if="said.can_write" variant="ghost" size="sm" icon="lucide-pencil" :aria-label="__('Edit Details')" @click="details" />
              </div>
              <div v-if="said.waits.length" class="flex flex-col gap-1.5">
                <button v-for="one in said.waits" :key="one.name" class="flex min-w-0 items-center gap-2 text-start text-base hover:underline" @click="go(`/desk/task/${encodeURIComponent(one.name)}`)">
                  <span class="lucide-circle-check size-4 shrink-0" :class="one.done ? 'text-ink-green-3' : 'text-ink-gray-4'" aria-hidden="true" />
                  <span class="truncate" :class="one.done ? 'text-ink-gray-5' : 'text-ink-gray-8'">{{ one.subject }}</span>
                </button>
              </div>
              <p v-else class="text-base text-ink-gray-5">{{ __("Nothing") }}</p>
            </section>
            <section v-if="said.blocking.length">
              <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ __("Waiting on This") }}</h3>
              <div class="flex flex-col gap-1.5">
                <button v-for="one in said.blocking" :key="one.name" class="flex min-w-0 items-center gap-2 text-start text-base hover:underline" @click="go(`/desk/task/${encodeURIComponent(one.name)}`)">
                  <span class="lucide-circle-dashed size-4 shrink-0 text-ink-gray-4" aria-hidden="true" />
                  <span class="truncate text-ink-gray-8">{{ one.subject }}</span>
                </button>
              </div>
            </section>
            <section>
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Details") }}</h3>
                <Button v-if="said.can_write" variant="ghost" size="sm" icon="lucide-pencil" :aria-label="__('Edit Details')" @click="details" />
              </div>
              <dl class="grid grid-cols-[7rem_minmax(0,1fr)] gap-y-2 text-base">
                <template v-for="one in facts" :key="one.label">
                  <dt class="text-ink-gray-5">{{ one.label }}</dt>
                  <dd class="truncate text-ink-gray-8">{{ one.value }}</dd>
                </template>
              </dl>
            </section>
          </aside>
        </div>
        <TaskTime v-else-if="view === 'time'" :said="said" @changed="load" />
        <TaskFiles v-else-if="view === 'files'" :task="said.name" :subject="said.subject" @count="(n) => (fileCount = n)" />
        <div v-else-if="view === 'activity'">
          <PlaceSpot :said="activitySpot" class="mb-3" />
          <Activity :key="said.name" doctype="Task" :name="said.name" />
        </div>
      </div>
    </template>
  </Page>
</template>

<script setup>
// A task's page (one_task/page/task_view): the task as one person works it
// all day, as a project's page is for a job. Its head, then Details, Time,
// Files and Activity. What it reads is one_task/view.py's `read`; what it
// changes it changes as desk does. Desk's own page head above it carries
// the main action and the rest (onedesk.island_page), from what `report` says.
import { computed, defineAsyncComponent, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Badge, Button, Checkbox, TextInput } from "frappe-ui";

import { Figures, Loading, Page, People, Pill, PlaceSpot, ViewTabs, __, call, date, follow, followList, go, hours, insert, isPast, onedesk, setQuery, setValue, useRecord } from "../kit";
import { DONE, PRIORITY, TASK_STATUS } from "../project/colors";
import Due from "../project/Due.vue";
import Title from "../project/Title.vue";
import { usePlace } from "../project/place";
import TaskFiles from "./TaskFiles.vue";
import TaskTime from "./TaskTime.vue";

// The timeline brings frappe-ui's editor, so it loads when first shown.
const Activity = defineAsyncComponent(() => import("../project/Activity.vue"));

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onStatus: Function,
  onActions: Function,
});

const TONE = { red: "text-ink-red-5", orange: "text-ink-amber-6", blue: "text-ink-blue-6" };
// A field that opens another record reads as a link.
const LINK = "text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-4 hover:decoration-ink-gray-8";

const name = computed(() => props.route[0]);
const said = ref(null);
const view = ref(props.query.view || "details");
const fileCount = ref(null);
// The record as its form has it: frappe's own menu items under the page's.
const record = useRecord("Task", name);

async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_task.view.read", { task: asked });
  if (asked !== name.value) return;
  said.value = got;
  if (fileCount.value === null) fileCount.value = got.files;
  report();
}

// Its sub-tasks and the time on it change on other records, so the page
// listens to those lists as well as to the task itself.
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
    fileCount.value = null;
    if (!now) return;
    stop = [follow("Task", now, load), followList("Task", soon), followList("Timesheet", soon)];
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(view, (now) => setQuery("view", now === "details" ? null : now));
watch(() => props.query.view, (now) => now && (view.value = now));
watch(() => said.value?.modified, (now, before) => now && before && now !== before && record.reload());
watch(record.record, () => said.value && report());

const VIEWS = computed(() =>
  [
    { key: "details", label: __("Details"), icon: "lucide-list-checks" },
    said.value?.time && { key: "time", label: __("Time"), icon: "lucide-clock", count: said.value.time.entries.length || null },
    { key: "files", label: __("Files"), icon: "lucide-paperclip", count: fileCount.value || null },
    { key: "activity", label: __("Activity"), icon: "lucide-activity" },
  ].filter(Boolean)
);

const day = (value) => (value ? String(value).slice(0, 10) : null);
const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const late = (one) => !DONE.includes(one.status) && isPast(day(one.exp_end_date));
const doneSteps = computed(() => said.value.steps.filter((one) => one.done).length);
const doneSubs = computed(() => said.value.sub_tasks.filter((one) => one.status === "Completed").length);

// The one thing worth saying above the task, if anything (view.py `headline`).
const headline = computed(() => {
  const line = said.value?.headline;
  if (!line) return "";
  if (line.key === "waiting") return __("Waiting on {0}", [line.names.join(", ")]);
  if (line.key === "review") return __("Waiting for review");
  if (line.key === "late") return line.days === 1 ? __("1 day late") : __("{0} days late", [line.days]);
  return __("Due today");
});

// How far along it is: the hours against the plan, the checklist and the
// sub-tasks, each only where the task has one.
const figures = computed(() => {
  const s = said.value;
  const list = [];
  const logged = s.time ? s.time.logged : s.actual_time || 0;
  if (s.expected_time || logged) {
    list.push({
      title: __("Logged"),
      value: hours(logged),
      note: s.expected_time ? __("of {0} planned", [hours(s.expected_time)]) : "",
      bar: s.expected_time ? Math.min(100, (logged / s.expected_time) * 100) : null,
      alarm: Boolean(s.expected_time && logged > s.expected_time),
    });
  }
  if (s.steps.length) list.push({ title: __("Checklist"), value: __("{0} of {1}", [doneSteps.value, s.steps.length]), bar: (doneSteps.value / s.steps.length) * 100 });
  if (s.sub_tasks.length) list.push({ title: __("Sub-tasks"), value: __("{0} of {1}", [doneSubs.value, s.sub_tasks.length]), bar: (doneSubs.value / s.sub_tasks.length) * 100 });
  if (!s.steps.length && s.progress) list.push({ title: __("Progress"), value: `${Math.round(s.progress)}%`, bar: s.progress });
  return list;
});

// What the Details column lists beside the work: the rest of the task, each
// only where it has a value.
const facts = computed(() => {
  const s = said.value;
  return [
    s.place && { label: __(s.place.kind), value: s.place.label },
    s.parent_task && { label: __("Parent Task"), value: s.above.at(-1)?.subject || s.parent_task },
    s.type && { label: __("Type"), value: s.type },
    s.is_milestone && s.one_bill_share && { label: __("Bill on Completion"), value: __("{0}% of the contract", [s.one_bill_share]) },
    s.review_date && { label: __("Review Date"), value: date(s.review_date) },
    s.completed_on && { label: __("Completed On"), value: date(s.completed_on) },
    s.completed_by && { label: __("Completed By"), value: s.people[s.completed_by]?.name || s.completed_by },
  ].filter(Boolean);
});

async function set(fieldname, value) {
  said.value[fieldname] = value;
  try {
    await setValue("Task", name.value, fieldname, value);
  } finally {
    load();
  }
}

const newStep = ref("");
const newSub = ref("");
async function tick(step, done) {
  step.done = done ? 1 : 0;
  await call("onedesk.one_task.task.tick", { task: name.value, step: step.name, done: done ? 1 : 0 });
  load();
}
async function addStep() {
  const text = newStep.value.trim();
  if (!text) return;
  newStep.value = "";
  await call("onedesk.one_task.task.add_step", { task: name.value, step: text });
  load();
}
async function addSub() {
  const text = newSub.value.trim();
  if (!text) return;
  newSub.value = "";
  await insert({ doctype: "Task", subject: text, parent_task: name.value, project: said.value.project || undefined });
  load();
}

const desk = onedesk;
const details = () => desk().task.edit(name.value, said.value.modified, load);
const describe = () => desk().task.edit(name.value, said.value.modified, load, ["description"]);

// Timing the task, as OneTask does (one_task/timer.py): one timer at a time.
const running = ref(null);
const timing = computed(() => running.value?.task === name.value);
async function time() {
  if (timing.value) {
    desk().task_timer?.stopped?.(await call("onedesk.one_task.timer.stop"));
    running.value = null;
  } else {
    running.value = await call("onedesk.one_task.timer.start", { task: name.value });
  }
  report();
  load();
}

function report() {
  const s = said.value;
  props.onTitle?.({
    title: s.subject,
    between: [
      s.place && { label: s.place.label, route: s.place.route },
      ...s.above.map((one) => ({ label: one.subject, route: `/desk/task/${encodeURIComponent(one.name)}` })),
    ].filter(Boolean),
  });
  props.onStatus?.(null);
  extended(s);
  props.onActions?.([...actions(s), ...verbs, ...record.menu({ gone: () => go("/desk/my-tasks") })]);
}
watch(name, async (now) => {
  running.value = now && said.value?.can_time !== false ? await call("onedesk.one_task.timer.running") : null;
}, { immediate: true });
watch(running, () => said.value && report());

// What can be done to the task, each only for whoever may do it.
function actions(s) {
  const list = [];
  if (s.can_write && !DONE.includes(s.status)) list.push({ label: __("Complete Task"), primary: true, onClick: () => set("status", "Completed") });
  if (s.can_write && DONE.includes(s.status)) list.push({ label: __("Reopen Task"), primary: true, onClick: () => set("status", "Open") });
  if (s.can_time || timing.value) list.push({ label: timing.value ? __("Stop Timer") : __("Start Timer"), button: true, onClick: time });
  if (s.can_write) list.push({ label: __("Edit Details"), onClick: details });
  if (s.can_write && !s.auto_repeat) list.push({ label: __("Repeat"), onClick: () => desk().project.repeat_task(s.name, load) });
  if (s.can_write && s.auto_repeat && !s.repeat?.disabled) list.push({ label: __("Stop Repeating"), onClick: () => desk().project.stop_repeat(s.name, load) });
  return list;
}

// The Activity view is a place of its own.
const activitySpot = usePlace("onetask_task.activity", () => (view.value === "activity" && said.value ? { task: { name: said.value.name, subject: said.value.subject } } : null));

// The workspace's extensions on the task's page (one_studio/places.py): those
// written for it are told the task, those written for a Task's head are told
// the record as its head is. Each is lent a note and a button, or a verb in
// the page's head, and drawn again with the page.
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
  if (places.listening("onetask_task.task")) {
    const task = {
      name: s.name,
      subject: s.subject,
      status: s.status,
      priority: s.priority,
      project: s.project,
      parent_task: s.parent_task,
      due: s.due,
      late_by: s.late_by,
      assigned: s.assigned,
      expected_time: s.expected_time,
      logged: s.time ? s.time.logged : s.actual_time,
      steps: { count: s.steps.length, done: doneSteps.value },
      sub_tasks: { count: s.sub_tasks.length, done: doneSubs.value },
      waiting: s.headline?.key === "waiting" ? s.headline.names : [],
    };
    places.emit("onetask_task.task", { task }, lend());
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
      "Task"
    );
    verbs = said;
  }
}
</script>
