<template>
  <!-- The time on the project and those under it, newest first, each entry
       with where it stands (one_project/hours.py). Its figures follow the
       kind: hours against the plan always, what's to invoice where hours are
       billed, and money only for whoever may see rates. -->
  <div class="pb-12 pt-2">
    <Loading v-if="!said" />
    <template v-else>
      <Section :title="__('Time')">
        <Figures :figures="figures" />
      </Section>

      <div class="mb-3 mt-5 flex flex-wrap items-center gap-2">
        <TabButtons v-model="shown" :options="FILTERS" />
        <Dropdown :options="groupChoices">
          <template #trigger><Button size="sm" icon-left="lucide-rows-3" :label="groupBy === 'none' ? __('Group By') : __('Group by {0}', [GROUPS()[groupBy]])" /></template>
        </Dropdown>
        <Button v-if="said.can_log" class="ms-auto" size="sm" variant="solid" icon-left="lucide-plus" :label="__('Log Time')" @click="logTime" />
      </div>

      <div v-if="!rows.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-clock size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ said.time === "Attendance on Site" ? __("No days on site") : __("No time logged") }}</p>
      </div>
      <List v-else :columns="{ base: ['6.5rem', 'minmax(0,1fr)', '3.5rem'], md: wide }" :row-height="said.has_sub_projects ? 52 : 44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Activity") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Task") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Hours") }}</ListHeaderCell>
          <ListHeaderCell v-if="said.money" class="justify-end max-md:hidden">{{ said.bills_hours ? __("Amount") : __("Cost") }}</ListHeaderCell>
          <ListHeaderCell class="max-md:hidden">{{ __("Status") }}</ListHeaderCell>
        </ListHeader>
        <ListGroup v-for="group in groups" :key="group.key">
          <template v-if="group.title !== null" #label>
            <span class="text-ink-gray-7">{{ group.title }}</span>
            <span class="ms-2 tabular-nums">{{ hours(group.hours) }}<template v-if="said.money && group.money"> · {{ amount(group.money) }}</template></span>
          </template>
          <ListRow v-for="item in group.rows" :key="item.name" @click="go(`/desk/timesheet/${item.timesheet}`)">
            <ListCell class="tabular-nums text-ink-gray-7">{{ date(item.date) }}</ListCell>
            <ListCell class="min-w-0 gap-2"><Avatar :label="item.who || item.user" :image="item.image" size="sm" /><span class="truncate text-ink-gray-8">{{ item.who || item.user }}</span></ListCell>
            <ListCell class="min-w-0 max-md:hidden"><span class="truncate text-ink-gray-7">{{ item.activity || "–" }}</span></ListCell>
            <ListCell class="min-w-0 max-md:hidden">
              <!-- The task, and under it where it is below this project. -->
              <span class="flex min-w-0 flex-col">
                <span v-if="item.task_subject || !item.where" class="truncate text-ink-gray-7">{{ item.task_subject || "–" }}</span>
                <span v-if="item.where" class="truncate text-ink-gray-5" :class="item.task_subject && 'text-sm'">{{ item.where }}</span>
              </span>
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ hours(item.hours) }}</ListCell>
            <ListCell v-if="said.money" class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ value(item) ? amount(value(item)) : "–" }}</ListCell>
            <ListCell class="max-md:hidden"><Badge :label="__(item.state)" :theme="STATE[item.state]" size="md" /></ListCell>
          </ListRow>
        </ListGroup>
      </List>
      <p v-if="said.more && shown === 'all'" class="mt-3 text-sm text-ink-gray-5">{{ __("{0} older entries", [said.more]) }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown, TabButtons } from "frappe-ui";
import { List, ListCell, ListGroup, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { Figures, Loading, Section, __, call, date, followList, go, hours, money, onedesk } from "../kit";
import { onlyArg, useOnly } from "./only";

const props = defineProps({
  projectName: { type: String, required: true },
  customer: String,
  title: String,
  tree: { type: Array, default: () => [] },
});
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();

const STATE = { Draft: "gray", "Not Billable": "gray", "To Invoice": "orange", Invoiced: "green" };
const FILTERS = [
  { value: "all", label: __("All") },
  { value: "Draft", label: __("Draft") },
  { value: "To Invoice", label: __("To Invoice") },
  { value: "Invoiced", label: __("Invoiced") },
  { value: "Not Billable", label: __("Not Billable") },
];
const GROUPS = () => ({ none: __("None"), who: __("Person"), activity: __("Activity"), task: __("Task"), project: __("Project") });
const shown = ref("all");
const groupBy = ref("none");
const said = ref(null);
// Money is in the company's currency, as ERPNext's base amounts are.
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

// The Amount or Cost column only for whoever sees money.
const wide = computed(() => ["6.5rem", "minmax(9rem,1fr)", "minmax(7rem,0.8fr)", "minmax(10rem,1.4fr)", "4.5rem", said.value?.money && "7rem", "7.5rem"].filter(Boolean));
const rows = computed(() => (said.value?.entries || []).filter((one) => shown.value === "all" || one.state === shown.value));

// The rows by what they're grouped by, each group with its hours and money.
const KEYS = {
  who: (one) => one.who || one.user || __("Nobody"),
  activity: (one) => one.activity || __("No activity"),
  task: (one) => one.task_subject || __("No task"),
  project: (one) => one.where || props.title,
};
const groups = computed(() => {
  if (groupBy.value === "none") return [{ key: "all", title: null, rows: rows.value }];
  const found = new Map();
  for (const one of rows.value) {
    const title = KEYS[groupBy.value](one);
    if (!found.has(title)) found.set(title, { key: title, title, rows: [], hours: 0, money: 0 });
    const group = found.get(title);
    group.rows.push(one);
    group.hours += one.hours;
    group.money += value(one) || 0;
  }
  return [...found.values()].sort((a, b) => b.hours - a.hours);
});
const groupChoices = computed(() =>
  Object.entries(GROUPS())
    .filter(([key]) => key !== "project" || said.value?.has_sub_projects)
    .map(([key, label]) => ({ label, selected: key === groupBy.value, onClick: () => (groupBy.value = key) }))
);

const figures = computed(() => {
  const s = said.value;
  const t = s.totals;
  const drafts = t.drafts ? __("{0} not submitted", [hours(t.drafts)]) : "";
  // A retainer's hours are billed with its month (Months, on the Overview).
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
      title: __("Logged"),
      value: hours(t.hours),
      note: [t.planned ? __("of {0} planned", [hours(t.planned)]) : "", drafts].filter(Boolean).join("\n"),
      bar: t.planned ? Math.min(100, Math.round((100 * t.hours) / t.planned)) : undefined,
      alarm: t.planned > 0 && t.hours > t.planned,
    },
    { title: __("This Month"), value: hours(t.month) },
  ];
  if (!s.money) return list;
  // What's to invoice where hours are billed, here or on a sub-project.
  if (s.bills_hours || t.to_invoice || t.invoiced) {
    list.push({
      title: __("To Invoice"),
      value: amount(t.to_invoice),
      note: !s.bills_hours && s.billing_on.length ? __("On {0}", [s.billing_on.join(", ")]) : "",
      action: s.can_invoice && t.to_invoice ? { icon: "lucide-receipt", label: __("Invoice Time"), onClick: invoiceTime } : null,
    });
    list.push({ title: __("Invoiced"), value: amount(t.invoiced) });
  }
  list.push({ title: __("Labour Cost"), value: amount(t.cost) });
  return list;
});

const logTime = () => onedesk().project.log_time(frm(), load);
const invoiceTime = () => onedesk().project.invoice_time(frm());
</script>
