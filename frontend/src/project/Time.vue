<template>
  <!-- The time logged on the project and those under it, newest first, each
       entry with where it stands (one_project/hours.py). -->
  <div class="pb-12 pt-2">
    <Loading v-if="!said" />
    <template v-else>
      <Section :title="__('Time')">
        <Figures :figures="figures" />
      </Section>

      <div class="mb-3 mt-5 flex flex-wrap items-center gap-2">
        <TabButtons v-model="shown" :options="FILTERS" />
        <Button v-if="said.can_log" class="ms-auto" size="sm" variant="solid" icon-left="lucide-plus" :label="__('Log Time')" @click="logTime" />
      </div>

      <div v-if="!rows.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-clock size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No time logged") }}</p>
      </div>
      <List v-else :columns="['6.5rem', 'minmax(9rem,1fr)', 'minmax(7rem,0.8fr)', 'minmax(10rem,1.4fr)', '4.5rem', '7rem', '7.5rem']" :row-height="44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Activity") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Task") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Hours") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" row-key="name" v-slot="{ item }">
          <ListRow @click="go(`/desk/timesheet/${item.timesheet}`)">
            <ListCell class="tabular-nums text-ink-gray-7">{{ date(item.date) }}</ListCell>
            <ListCell class="min-w-0 gap-2"><Avatar :label="item.who || item.user" size="sm" /><span class="truncate text-ink-gray-8">{{ item.who || item.user }}</span></ListCell>
            <ListCell class="min-w-0"><span class="truncate text-ink-gray-7">{{ item.activity || "–" }}</span></ListCell>
            <ListCell class="min-w-0">
              <span class="truncate text-ink-gray-7">{{ item.task_subject || "–" }}<span v-if="item.project !== projectName" class="text-ink-gray-5"> · {{ item.project_title }}</span></span>
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ hours(item.hours) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ item.amount ? amount(item.amount) : "–" }}</ListCell>
            <ListCell><Badge :label="__(item.state)" :theme="STATE[item.state]" size="md" /></ListCell>
          </ListRow>
        </ListRows>
      </List>
      <p v-if="said.more && shown === 'all'" class="mt-3 text-sm text-ink-gray-5">{{ __("{0} older entries", [said.more]) }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, TabButtons } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Section, __, call, date, followList, go, hours, money, onedesk } from "../kit";

const props = defineProps({
  projectName: { type: String, required: true },
  customer: String,
  currency: String,
  tree: { type: Array, default: () => [] },
});

const STATE = { Draft: "gray", "Not Billable": "gray", "To Invoice": "orange", Invoiced: "green" };
const FILTERS = [
  { value: "all", label: __("All") },
  { value: "To Invoice", label: __("To Invoice") },
  { value: "Draft", label: __("Draft") },
];
const shown = ref("all");
const said = ref(null);
const amount = (value) => money(value, props.currency);
const frm = () => ({ doctype: "Project", doc: { name: props.projectName, customer: props.customer }, tree: props.tree });

async function load() {
  said.value = await call("onedesk.one_project.hours.entries", { project: props.projectName });
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

const rows = computed(() => (said.value?.entries || []).filter((one) => shown.value === "all" || one.state === shown.value));
const figures = computed(() => {
  const t = said.value.totals;
  return [
    { title: __("This Month"), value: hours(t.month) },
    { title: __("All Time"), value: hours(t.hours), note: t.drafts ? __("{0} not submitted", [hours(t.drafts)]) : "" },
    {
      title: __("To Invoice"),
      value: amount(t.to_invoice),
      action: said.value.can_invoice && t.to_invoice ? { icon: "lucide-receipt", label: __("Invoice Time"), onClick: invoiceTime } : null,
    },
    { title: __("Invoiced"), value: amount(t.invoiced) },
  ];
});

const logTime = () => onedesk().project.log_time(frm(), load);
const invoiceTime = () => onedesk().project.invoice_time(frm());
</script>
