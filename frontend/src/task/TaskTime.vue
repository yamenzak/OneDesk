<template>
  <!-- The time logged on the task, newest first, as the reader may read
       timesheets (one_task/view.py `_time`): who, the day, the activity and
       the hours, a draft said as one. -->
  <div class="pb-12">
    <PlaceSpot :said="spot" class="mb-3" />
    <div class="flex flex-wrap items-center gap-2 pb-2">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-clock size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Time") }}
        <span v-if="time.entries.length" class="text-base font-normal text-ink-gray-5">{{ time.entries.length }}</span>
      </h2>
      <Button v-if="said.project && said.can_time" size="sm" variant="solid" icon-left="lucide-plus" :label="__('Log Time')" @click="logTime" />
    </div>
    <Figures class="mb-5 mt-3" :figures="figures" />

    <div v-if="!time.entries.length" class="flex flex-col items-center gap-3 py-16 text-center">
      <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-clock size-5" /></span>
      <p class="text-base text-ink-gray-7">{{ __("No time logged") }}</p>
    </div>
    <List v-else :columns="{ base: ['6.5rem', 'minmax(0,1fr)', '3.5rem'], md: ['7rem', 'minmax(0,1fr)', 'minmax(0,1fr)', '4.5rem', '6rem'] }" :row-height="44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
      <ListHeader>
        <ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
        <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
        <ListHeaderCell class="max-md:hidden">{{ __("Activity") }}</ListHeaderCell>
        <ListHeaderCell class="justify-end">{{ __("Hours") }}</ListHeaderCell>
        <ListHeaderCell class="max-md:hidden">{{ __("Status") }}</ListHeaderCell>
      </ListHeader>
      <ListRow v-for="(item, i) in shown" :key="`${item.sheet}-${i}`" @click="go(`/desk/timesheet/${encodeURIComponent(item.sheet)}`)">
        <ListCell class="text-ink-gray-7">{{ date(item.day) }}</ListCell>
        <ListCell class="min-w-0 gap-2"><Avatar :label="item.who || item.user" :image="said.people[item.user]?.image" size="sm" /><span class="truncate text-ink-gray-8">{{ item.who || item.user }}</span></ListCell>
        <ListCell class="min-w-0 max-md:hidden"><span class="truncate text-ink-gray-7">{{ item.activity || "–" }}</span></ListCell>
        <ListCell class="justify-end tabular-nums text-ink-gray-8">{{ hours(item.hours) }}</ListCell>
        <ListCell class="max-md:hidden"><Badge v-if="item.draft" :label="__('Draft')" theme="gray" size="md" /></ListCell>
      </ListRow>
      <!-- The rest, a page at a time. -->
      <ListRow v-if="time.entries.length > shown.length" @click="page += PAGE">
        <ListCell class="text-ink-gray-5">{{ __("Show {0} More", [Math.min(PAGE, time.entries.length - shown.length)]) }}</ListCell>
      </ListRow>
    </List>
    <Button v-if="time.more" class="mt-3" variant="ghost" icon-right="lucide-arrow-up-right" :label="__('Open Older Entries')" @click="go(`/desk/timesheet?task=${encodeURIComponent(said.name)}`)" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Avatar, Badge, Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { Figures, PlaceSpot, __, date, go, hours, onedesk } from "../kit";
import { usePlace } from "../project/place";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const time = computed(() => props.said.time);

// Who logged the hours, most first, and what is still in draft. The head
// already says the total against the plan.
const figures = computed(() => {
  const by = {};
  for (const one of time.value.entries) {
    const who = one.who || one.user || "";
    by[who] = (by[who] || 0) + one.hours;
  }
  const people = Object.entries(by)
    .sort((a, b) => b[1] - a[1])
    .slice(0, time.value.drafts ? 3 : 4)
    .map(([who, total]) => ({ title: who, value: hours(Math.round(total * 10) / 10) }));
  return [...people, time.value.drafts && { title: __("Not Submitted"), value: hours(time.value.drafts) }].filter(Boolean);
});

const PAGE = 20;
const page = ref(PAGE);
const shown = computed(() => time.value.entries.slice(0, page.value));

const spot = usePlace("onetask_task.time", () => ({
  task: { name: props.said.name, subject: props.said.subject },
  time: { logged: time.value.logged, drafts: time.value.drafts, planned: props.said.expected_time || 0, entries: time.value.entries.length },
}));

const logTime = () => onedesk().task.log_time(props.said.name, props.said.project, props.said.bills_hours, () => emit("changed"));
</script>
