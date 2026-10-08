<template>
  <!-- The project's history across it and its sub-projects: the documents
       made for it, its tasks, time, updates and files (one_project/activity.py),
       beside frappe's own timeline of the project, its comments, emails and
       field changes, newest first as a form's Activity is. A comment is
       written at the top and New Email opens frappe's Email dialog (kit
       ActivityComposer); an email is answered from its own row with Reply or
       Reply All. -->
  <div class="flex flex-col gap-4 pb-10">
    <ActivityComposer ref="composer" doctype="Project" :name="project" :vet="letIn" @sent="sent">
      <TabButtons v-model="shown" :options="FILTERS" />
    </ActivityComposer>
    <!-- What the workspace's extensions add here (one_studio/places.py). -->
    <PlaceSpot :said="spot" />
    <ActivityTimeline :activities="rows" :loading="!ready" :paginate="paginate">
      <template #empty>
        <div class="py-12 text-center text-base text-ink-gray-5">{{ __("No activity") }}</div>
      </template>

      <template v-for="(icon, type) in ICONS" #[`icon-${type}`]="{ activity }">
        <span :class="[iconOf(activity, icon), 'size-4 text-ink-gray-6']" />
      </template>

      <template #item-email="{ activity: one }">
        <EmailItem :email="one">
          <template #actions>
            <Button variant="ghost" size="sm" icon="lucide-reply" :tooltip="__('Reply')" :aria-label="__('Reply')" @click="composer?.reply(one)" />
            <Button variant="ghost" size="sm" icon="lucide-reply-all" :tooltip="__('Reply All')" :aria-label="__('Reply All')" @click="composer?.reply(one, true)" />
          </template>
        </EmailItem>
      </template>

      <template #item-document="{ activity: one }">
        <ActivityLine :activity="one" :aside="[one.data.party, one.data.amount ? money(one.data.amount, one.data.currency) : '', one.data.sub_project].filter(Boolean).join(' · ')">
          {{ VERBS()[one.data.verb] }} {{ __(one.data.doctype) }}
          <a class="text-ink-gray-8 hover:text-ink-blue-5" :href="one.data.route" @click.prevent="go(one.data.route)">{{ one.data.name }}</a>
        </ActivityLine>
      </template>

      <template #item-tasks="{ activity: one }">
        <ActivityLine :activity="one" :aside="one.data.sub_project">
          <template v-if="one.data.count === 1">
            {{ __("added task") }}
            <button class="text-ink-gray-8 hover:text-ink-blue-5" @click="$emit('task', one.data.tasks[0].name)">{{ one.data.tasks[0].subject }}</button>
          </template>
          <template v-else>
            {{ __("added {0} tasks", [one.data.count]) }}
            <span class="text-ink-gray-5">({{ andList([...one.data.tasks.map((task) => task.subject), ...(one.data.count > 3 ? [__("{0} more", [one.data.count - 3])] : [])]) }})</span>
          </template>
        </ActivityLine>
      </template>

      <template #item-task="{ activity: one }">
        <ActivityLine :activity="one" :aside="one.data.sub_project">
          {{ __("completed") }}
          <button class="text-ink-gray-8 hover:text-ink-blue-5" @click="$emit('task', one.data.name)">{{ one.data.subject }}</button>
        </ActivityLine>
      </template>

      <template #item-time="{ activity: one }">
        <ActivityLine :activity="one" :aside="one.data.sub_project">{{ one.data.days > 1 ? __("logged {0} over {1} days", [hours(one.data.hours), one.data.days]) : __("logged {0}", [hours(one.data.hours)]) }}</ActivityLine>
      </template>

      <template #item-update="{ activity: one }">
        <ActivityLine :activity="one" :aside="one.data.sub_project">
          {{ __("posted an update") }}
          <template #below>
            <div class="rounded-2 bg-surface-gray-2 px-3 py-2 text-base font-normal text-ink-gray-8">
              <Badge v-if="one.data.health" class="mb-1" :label="__(one.data.health)" :theme="HEALTH[one.data.health] || 'gray'" size="sm" />
              <p class="whitespace-pre-line">{{ one.data.text }}</p>
            </div>
          </template>
        </ActivityLine>
      </template>

      <template #item-files="{ activity: one }">
        <ActivityLine :activity="one" :aside="[andList(one.data.names), one.data.sub_project].filter(Boolean).join(' · ')">{{ filesSaid(one.data) }}</ActivityLine>
      </template>

      <template #item-started="{ activity: one }">
        <ActivityLine :activity="one">
          <template v-if="one.data.sub">
            {{ __("started sub-project") }}
            <a class="text-ink-gray-8 hover:text-ink-blue-5" :href="`/desk/project/${one.data.name}`" @click.prevent="go(`/desk/project/${one.data.name}`)">{{ one.data.title }}</a>
          </template>
          <template v-else>{{ __("created the project") }}</template>
        </ActivityLine>
      </template>
    </ActivityTimeline>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Badge, Button, TabButtons } from "frappe-ui";
import { ActivityTimeline, EmailItem, useActivityTimeline } from "@framework/ui/ActivityTimeline";

import { ActivityComposer, PlaceSpot, __, andList, ask, call, followList, go, hours, listen, money } from "../kit";
import { onlyArg, useOnly } from "./only";
import ActivityLine from "./ActivityLine.vue";
import { usePlace } from "./place";

const props = defineProps({ project: { type: String, required: true }, modified: String });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();
defineEmits(["task"]);

// What of the project's own fields its timeline shows (Project tracks its changes).
const FIELDS = ["project_name", "status", "one_health", "one_manager", "customer", "expected_start_date", "expected_end_date", "estimated_costing", "priority", "one_kind", "users"];
const own = useActivityTimeline("Project", props.project, ["comment", "email", { version: FIELDS }]);

const FILTERS = [
  { label: __("All"), value: "all" },
  { label: __("Money"), value: "money" },
  { label: __("Work"), value: "work" },
  { label: __("Comments"), value: "comments" },
];
const shown = ref("all");
const VERBS = () => ({ created: __("created"), submitted: __("submitted"), cancelled: __("cancelled") });
const HEALTH = { "On Track": "green", "At Risk": "orange", "Off Track": "red" };
// The gutter icon of each kind of row; a cancelled document and photos have their own.
const ICONS = { document: "lucide-file-text", tasks: "lucide-list-plus", task: "lucide-circle-check", time: "lucide-clock", update: "lucide-message-square-text", files: "lucide-paperclip", started: "lucide-folder-plus" };
const iconOf = (one, icon) => (one.data.verb === "cancelled" ? "lucide-file-x" : one.type === "files" && one.data.photos ? "lucide-image" : icon);
function filesSaid(data) {
  if (data.removed) return data.count === 1 ? __("removed a file") : __("removed {0} files", [data.count]);
  if (data.photos) return data.count === 1 ? __("added a photo") : __("added {0} photos", [data.count]);
  return data.count === 1 ? __("added a file") : __("added {0} files", [data.count]);
}

// The project's history (activity.py), a page at a time, newest first.
const history = ref([]);
const more = ref(false);
const fetching = ref(false);
const ready = ref(false);
async function load(older = false) {
  fetching.value = true;
  try {
    const before = older ? history.value.reduce((oldest, one) => (one.timestamp < oldest ? one.timestamp : oldest), "9999") : null;
    const said = await call("onedesk.one_project.activity.activity", { project: props.project, before, ...onlyArg(only) });
    const kept = older ? history.value : [];
    const seen = new Set(kept.map((one) => one.key));
    history.value = [...kept, ...said.activities.filter((one) => !seen.has(one.key))];
    more.value = said.more;
  } finally {
    fetching.value = false;
    ready.value = true;
  }
}
const paginate = reactive({
  hasNextPage: computed(() => more.value),
  isFetchingNextPage: computed(() => fetching.value),
  fetchNextPage: () => load(true),
  isPagedRow: (one) => Boolean(one.kind),
  loadMore: { position: "bottom", label: __("Show earlier activity"), icon: "lucide-chevrons-down" },
});

const kindOf = (one) => one.kind || (one.type === "version" ? "work" : "comments");
const rows = computed(() =>
  [...(own.activities.value || []), ...history.value]
    .filter((one) => shown.value === "all" || kindOf(one) === shown.value)
    .sort((a, b) => (b.timestamp || "").localeCompare(a.timestamp || ""))
);
const spot = usePlace("oneproject.activity", () => ready.value && { project: { name: props.project }, activity: { shown: shown.value, count: rows.value.length } });

// Anything that adds to the history reloads its newest page: money moving
// (money.py tells the page), a task, time or an update, the project saved.
let soon;
const later = () => {
  clearTimeout(soon);
  soon = setTimeout(() => load(), 400);
};
const stops = [
  listen("one_project_money", (data) => data.project === props.project && later()),
  followList("Task", later),
  followList("Timesheet", later),
  followList("Project Update", later),
];
onBeforeUnmount(() => stops.forEach((stop) => stop()));
watch(() => props.modified, later);
load();

// Somebody mentioned who can't open the project hears of it but can't come
// in, so whoever may change the project is asked to add them first
// (one_project/members.py `unseen`, `let_in`). The comment is posted either way.
async function letIn(body) {
  const said = await call("onedesk.one_project.members.unseen", { project: props.project, content: body });
  if (!said.people.length || !said.can_add) return;
  const names = andList(said.people.map((one) => one.name));
  if (await ask(__("{0} can't see this project. Add them to it?", [names]), __("Add to Project"), __("Just Comment")))
    await call("onedesk.one_project.members.let_in", { project: props.project, users: said.people.map((one) => one.user) });
}

// What was written at the foot shows at once; a filter that hides it gives way.
const composer = ref(null);
function sent() {
  if (shown.value === "money" || shown.value === "work") shown.value = "all";
  own.reload?.();
}
</script>
