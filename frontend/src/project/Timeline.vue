<template>
  <!-- When each task runs, week by week, with today marked: the plan at a glance. -->
  <div class="pb-12 pt-4">
    <div v-if="!rows.length" class="py-16 text-center text-base text-ink-gray-5">{{ __("No tasks with dates") }}</div>
    <div v-else class="overflow-x-auto rounded-5 border border-outline-gray-2">
      <div class="relative min-w-[56rem]">
        <div class="grid grid-cols-[16rem_minmax(0,1fr)] border-b border-outline-gray-2 bg-surface-gray-1 text-sm text-ink-gray-5">
          <div class="px-3 py-2">{{ __("Task") }}</div>
          <div class="relative h-full">
            <span v-for="week in weeks" :key="week.at" class="absolute top-2 -translate-x-1/2 whitespace-nowrap" :style="{ insetInlineStart: `${week.at}%` }">{{ week.label }}</span>
          </div>
        </div>
        <template v-for="group in grouped" :key="group.key">
          <div class="border-b border-outline-gray-1 bg-surface-gray-1 px-3 py-1.5 text-sm font-medium text-ink-gray-7">{{ group.title }}</div>
          <div v-for="row in group.rows" :key="row.task.name" class="grid grid-cols-[16rem_minmax(0,1fr)] border-b border-outline-gray-1 last:border-0">
            <button class="truncate px-3 py-2 text-start text-base text-ink-gray-8 hover:underline" @click="$emit('open', row.task.name)">{{ row.task.subject }}</button>
            <div class="relative">
              <span v-for="week in weeks" :key="week.at" class="absolute inset-y-0 border-s border-outline-gray-1" :style="{ insetInlineStart: `${week.at}%` }" />
              <button
                class="absolute top-1/2 h-5 -translate-y-1/2 rounded-3"
                :class="[SURFACE[TASK_STATUS[row.task.status] || 'gray'], row.task.is_milestone && 'w-3 rotate-45']"
                :style="row.task.is_milestone ? { insetInlineStart: `${row.end}%` } : { insetInlineStart: `${row.start}%`, width: `${Math.max(row.end - row.start, 1)}%` }"
                :aria-label="row.task.subject"
                @click="$emit('open', row.task.name)"
              />
            </div>
          </div>
        </template>
        <span v-if="today !== null" class="pointer-events-none absolute inset-y-0 border-s-2 border-outline-red-3" :style="{ insetInlineStart: `calc(16rem + (100% - 16rem) * ${today / 100})` }" />
      </div>
    </div>
    <p v-if="rows.length && undated" class="mt-3 text-sm text-ink-gray-5">{{ undated === 1 ? __("1 task without dates") : __("{0} tasks without dates", [undated]) }}</p>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { __, shortDate } from "../kit";
import { SURFACE, TASK_STATUS } from "./colors";

const props = defineProps({ work: { type: Object, required: true }, groups: { type: Array, required: true } });
defineEmits(["open"]);

const DAY = 86400000;
const day = (value) => new Date(`${value}T00:00:00`).getTime();
const dated = computed(() => props.groups.flatMap((g) => g.tasks).filter((t) => t.exp_end_date));
const range = computed(() => {
  const starts = dated.value.map((t) => day(t.exp_start_date || t.exp_end_date) - (t.exp_start_date ? 0 : 3 * DAY));
  const ends = dated.value.map((t) => day(t.exp_end_date));
  const todayAt = day(props.work.today);
  const from = Math.min(...starts, todayAt) - 3 * DAY;
  const to = Math.max(...ends, todayAt) + 7 * DAY;
  return { from, to, span: to - from };
});
const at = (time) => (100 * (time - range.value.from)) / range.value.span;
const row = (task) => ({
  task,
  start: at(day(task.exp_start_date || task.exp_end_date) - (task.exp_start_date ? 0 : 3 * DAY)),
  end: at(day(task.exp_end_date) + DAY),
});
const grouped = computed(() =>
  props.groups.map((g) => ({ key: g.key, title: g.title, rows: g.tasks.filter((t) => t.exp_end_date).map(row) })).filter((g) => g.rows.length)
);
const rows = computed(() => grouped.value.flatMap((g) => g.rows));
const undated = computed(() => props.groups.flatMap((g) => g.tasks).filter((t) => !t.exp_end_date).length);
const weeks = computed(() => {
  const out = [];
  const start = new Date(range.value.from);
  start.setDate(start.getDate() + ((8 - start.getDay()) % 7));
  for (let time = start.getTime(); time < range.value.to; time += 7 * DAY) {
    out.push({ at: at(time), label: shortDate(new Date(time).toISOString().slice(0, 10)) });
  }
  return out;
});
const today = computed(() => (dated.value.length ? at(day(props.work.today)) : null));
</script>
