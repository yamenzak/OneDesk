<template>
  <div class="pb-12">
    <Loading v-if="!said" />
    <template v-else>
      <PlaceSpot :said="spot" class="mb-3" />
      <div class="flex flex-wrap items-center gap-2 pb-2">
        <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
          <span class="lucide-clock size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Timesheet") }}
          <span v-if="counted" class="text-base font-normal text-ink-gray-5">{{ counted }}</span>
        </h2>
        <TabButtons v-if="filters.length > 1" v-model="shown" :options="filters" />
        <Dropdown :options="groupChoices">
          <template #trigger><Button size="sm" icon-left="lucide-rows-3" :label="__('Group by {0}', [GROUPS()[groupBy]])" /></template>
        </Dropdown>
        <Button v-if="said.can_log" size="sm" variant="solid" icon-left="lucide-plus" :label="__('Log Time')" @click="logTime" />
      </div>
      <Figures class="mb-5 mt-3" :figures="figures" />

      <div v-if="!rows.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-clock size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ said.time === "Attendance on Site" ? __("No days on site") : __("No time logged") }}</p>
      </div>
      <List v-else :columns="{ base: byOthers ? ['6.5rem', 'minmax(0,1fr)', '3.5rem'] : ['6.5rem', '3.5rem'], md: wide }" :row-height="said.has_sub_projects ? 52 : 44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell v-if="byOthers">{{ __("Person") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Activity") }}</ListHeaderCell>
          <ListHeaderCell v-if="hasTask" class="max-md:hidden">{{ __("Task") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Hours") }}</ListHeaderCell>
          <ListHeaderCell v-if="said.money" class="justify-end max-md:hidden">{{ said.bills_hours ? __("Amount") : __("Cost") }}</ListHeaderCell>
          <ListHeaderCell v-if="hasStatus" class="max-md:hidden">{{ __("Status") }}</ListHeaderCell>
        </ListHeader>
        <ListGroup v-for="group in paged" :key="group.key">
          <template v-if="group.title !== null" #label>
            <span class="text-ink-gray-7">{{ group.title }}</span>
            <span class="ms-2 tabular-nums">{{ hours(Math.round(group.hours * 10) / 10) }}<template v-if="said.money && group.money"> · {{ amount(group.money) }}</template></span>
          </template>
          <ListRow v-for="item in group.shown" :key="item.name" @click="go(`/desk/timesheet/${item.timesheet}`)">
            <ListCell class="text-ink-gray-7">{{ date(item.date) }}</ListCell>
            <ListCell v-if="byOthers" class="min-w-0 gap-2"><Avatar :label="item.who || item.user" :image="item.image" size="sm" /><span class="truncate text-ink-gray-8">{{ item.who || item.user }}</span></ListCell>
            <ListCell class="min-w-0 max-md:hidden"><span class="truncate text-ink-gray-7">{{ item.activity || "–" }}</span></ListCell>
            <ListCell v-if="hasTask" class="min-w-0 max-md:hidden">
              <span class="flex min-w-0 flex-col">
                <span v-if="item.task_subject || !item.where" class="truncate text-ink-gray-7">{{ item.task_subject || "–" }}</span>
                <span v-if="item.where" class="truncate text-ink-gray-5" :class="item.task_subject && 'text-sm'">{{ item.where }}</span>
              </span>
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ hours(item.hours) }}</ListCell>
            <ListCell v-if="said.money" class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ value(item) ? amount(value(item)) : "–" }}</ListCell>
            <ListCell v-if="hasStatus" class="max-md:hidden"><Badge v-if="billable || item.state === 'Draft'" :label="__(item.state)" :theme="STATE[item.state]" size="md" /></ListCell>
          </ListRow>
          <ListRow v-if="group.rows.length > group.shown.length" @click="more[group.key] = group.shown.length + PAGE">
            <ListCell class="text-ink-gray-5">{{ __("Show {0} More", [Math.min(PAGE, group.rows.length - group.shown.length)]) }}</ListCell>
          </ListRow>
        </ListGroup>
      </List>
      <Button v-if="said.more && shown === 'all'" class="mt-3" variant="ghost" size="sm" icon-right="lucide-arrow-up-right" :label="__('Open {0} Older Entries', [said.more])" @click="go(said.all_route)" />
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown, TabButtons } from "frappe-ui";
import { List, ListCell, ListGroup, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { Figures, Loading, PlaceSpot, __, call, date, followList, go, hours, money, onedesk } from "../kit";
import { usePlace } from "./place";
import { onlyArg, useOnly } from "./only";

const props = defineProps({
  projectName: { type: String, required: true },
  customer: String,
  title: String,
  tree: { type: Array, default: () => [] },
});
const only = useOnly();

const STATE = { Draft: "gray", "Not Billable": "gray", "To Invoice": "amber", Invoiced: "green" };
const FILTERS = [
  { value: "all", label: __("All") },
  { value: "Draft", label: __("Draft") },
  { value: "To Invoice", label: __("To Invoice") },
  { value: "Invoiced", label: __("Invoiced") },
  { value: "Not Billable", label: __("Not Billable") },
];
const PAGE = 25;
const FIRST = 5;
const more = reactive({});
const GROUPS = () => ({ none: __("None"), who: __("Person"), activity: __("Activity"), task: __("Task"), project: __("Project") });
const shown = ref("all");
const groupBy = ref("who");
const said = ref(null);
const amount = (value) => money(value, said.value?.currency);
const value = (item) => (said.value.bills_hours ? item.amount : item.cost);
const frm = () => ({ doctype: "Project", doc: { name: props.projectName, project_name: props.title, customer: props.customer }, tree: props.tree, bills_hours: said.value?.bills_hours });

async function load() {
  said.value = await call("onedesk.one_project.hours.entries", { project: props.projectName, ...onlyArg(only) });
}
let timer = null;
const stop = followList("Timesheet", () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
});
onBeforeUnmount(() => {
  stop();
  clearTimeout(timer);
});
watch(() => props.projectName, load, { immediate: true });

const byOthers = computed(() => groupBy.value !== "who");
const wide = computed(() => ["6.5rem", byOthers.value && "minmax(9rem,1fr)", "minmax(7rem,0.8fr)", hasTask.value && "minmax(10rem,1.4fr)", "4.5rem", said.value?.money && "7rem", hasStatus.value && "7.5rem"].filter(Boolean));
const rows = computed(() => (said.value?.entries || []).filter((one) => shown.value === "all" || one.state === shown.value));
const counted = computed(() => (said.value?.sums || []).reduce((sum, one) => sum + (shown.value === "all" || one.state === shown.value ? one.entries : 0), 0));
watch([shown, groupBy], () => Object.keys(more).forEach((key) => delete more[key]));
const entries = computed(() => said.value?.entries || []);
const billable = computed(() => said.value?.bills_hours || entries.value.some((one) => ["To Invoice", "Invoiced"].includes(one.state)));
const hasStatus = computed(() => billable.value || entries.value.some((one) => one.state === "Draft"));
const hasTask = computed(() => entries.value.some((one) => one.task_subject || one.where));
const filters = computed(() => FILTERS.filter((one) => one.value === "all" || entries.value.some((entry) => entry.state === one.value && (billable.value || one.value === "Draft"))));
const paged = computed(() =>
  groups.value.map((group) => ({ ...group, shown: group.rows.slice(0, more[group.key] || (group.title === null ? PAGE : FIRST)) }))
);

const KEYS = {
  who: (one) => one.who || one.user || __("Nobody"),
  activity: (one) => one.activity || __("No activity"),
  task: (one) => one.task_subject || __("No task"),
  project: (one) => one.where || props.title,
};
const groups = computed(() => {
  if (groupBy.value === "none") return [{ key: "all", title: null, rows: rows.value }];
  const found = new Map();
  const group = (title) => {
    if (!found.has(title)) found.set(title, { key: title, title, rows: [], hours: 0, money: 0 });
    return found.get(title);
  };
  for (const one of said.value.sums || []) {
    if (shown.value !== "all" && one.state !== shown.value) continue;
    const into = group(KEYS[groupBy.value](one));
    into.hours += one.hours;
    into.money += value(one) || 0;
  }
  for (const one of rows.value) group(KEYS[groupBy.value](one)).rows.push(one);
  return [...found.values()].filter((one) => one.rows.length).sort((a, b) => b.hours - a.hours);
});
const groupChoices = computed(() =>
  Object.entries(GROUPS())
    .filter(([key]) => key !== "project" || said.value?.has_sub_projects)
    .map(([key, label]) => ({ label, selected: key === groupBy.value, onClick: () => (groupBy.value = key) }))
);

const spot = usePlace("oneproject.time", () =>
  said.value && {
    project: { name: props.projectName, title: props.title, customer: props.customer || null },
    time: {
      entries: counted.value,
      hours: said.value.totals.hours,
      planned: said.value.totals.planned || null,
      month: said.value.totals.month,
      drafts: said.value.totals.drafts || 0,
      allowance: said.value.allowance ?? null,
    },
  }
);
const figures = computed(() => {
  const s = said.value;
  const t = s.totals;
  const drafts = t.drafts ? __("{0} not submitted", [hours(t.drafts)]) : "";
  if (s.allowance != null)
    return [
      {
        title: __("This Month"),
        value: hours(t.month),
        note: s.allowance ? __("of {0} a month", [hours(s.allowance)]) : "",
        bar: s.allowance ? Math.min(100, Math.round((100 * t.month) / s.allowance)) : undefined,
        alarm: s.allowance > 0 && t.month > s.allowance,
      },
      { title: __("All Time"), value: hours(t.hours), note: drafts },
    ];
  const list = [
    {
      title: __("Actual Time"),
      value: hours(t.hours),
      note: [t.planned ? __("of {0} planned", [hours(t.planned)]) : "", drafts].filter(Boolean).join("\n"),
      action: !t.planned && s.can_budget ? { icon: "lucide-plus", label: __("Set Planned Hours"), onClick: setBudget } : null,
      bar: t.planned ? Math.min(100, Math.round((100 * t.hours) / t.planned)) : undefined,
      alarm: t.planned > 0 && t.hours > t.planned,
    },
    { title: __("This Month"), value: hours(t.month) },
  ];
  if (!s.money) return list;
  if (s.bills_hours || t.to_invoice || t.invoiced) {
    list.push({
      title: __("To Invoice"),
      value: amount(t.to_invoice),
      note: !s.bills_hours && s.billing_on.length ? __("On {0}", [s.billing_on.join(", ")]) : "",
      action: s.can_invoice && t.to_invoice ? { icon: "lucide-receipt", label: __("Invoice Time"), onClick: invoiceTime } : null,
    });
    list.push({ title: __("Invoiced"), value: amount(t.invoiced) });
  }
  list.push({
    title: __("Total Costing Amount"),
    value: amount(t.cost),
    note: t.time_budget ? __("of {0} budget", [amount(t.time_budget)]) : "",
    bar: t.time_budget ? Math.min(100, Math.round((100 * t.cost) / t.time_budget)) : undefined,
    alarm: t.time_budget > 0 && t.cost > t.time_budget,
    action: !t.time_budget && s.can_budget ? { icon: "lucide-plus", label: __("Set Time Budget"), onClick: setBudget } : null,
  });
  return list;
});

const setBudget = () => onedesk().project.budget(frm(), load);
const logTime = () => onedesk().project.log_time(frm(), load);
const invoiceTime = () => onedesk().project.invoice_time(frm());
</script>
