<template>
  <div>
    <div class="max-md:hidden">
      <div class="grid grid-cols-[9rem_minmax(0,1fr)_4rem] gap-x-4">
        <div />
        <div class="relative h-5 text-xs text-ink-gray-5">
          <span v-for="tick in ticks" :key="tick.day" class="absolute -translate-x-1/2 whitespace-nowrap" :style="{ left: `${tick.at}%` }">{{ tick.label }}</span>
        </div>
        <div />
      </div>
      <div class="relative mb-5">
        <div v-if="now !== null" class="pointer-events-none absolute inset-y-0 z-[1] grid w-full grid-cols-[9rem_minmax(0,1fr)_4rem] gap-x-4">
          <div />
          <div class="relative">
            <span class="absolute inset-y-0 w-px bg-surface-gray-5" :style="{ left: `${now}%` }" />
            <span class="absolute -bottom-5 -translate-x-1/2 text-xs text-ink-gray-5" :style="{ left: `${now}%` }">{{ __("Today") }}</span>
          </div>
        </div>
        <div v-for="lane in rows" :key="lane.key" class="grid grid-cols-[9rem_minmax(0,1fr)_4rem] items-start gap-x-4 border-b border-outline-gray-1 py-3 last:border-b-0">
          <button class="min-w-0 truncate text-start text-base text-ink-gray-8 hover:underline" @click="openLane(lane)">{{ lane.title }}</button>
          <div class="relative h-10">
            <span class="absolute inset-x-0 top-[5px] h-0.5 bg-surface-gray-3" />
            <Tooltip v-for="one in lane.dated" :key="one.name" :text="tip(one)">
              <button class="absolute top-0 z-[2] h-3 w-3 -translate-x-1/2 rounded-full border" :class="ring(one, lane)" :style="{ left: `${one.at}%` }" :aria-label="tip(one)" @click="go(`/desk/task/${one.name}`)" />
            </Tooltip>
            <div v-if="lane.next && lane.next.at !== undefined" class="absolute top-4 max-w-[60%] truncate text-sm" :class="lane.next.at > 60 ? '-translate-x-full text-end' : ''" :style="{ left: `${lane.next.at}%` }">
              <span class="text-ink-gray-8">{{ lane.next.subject }}</span>
              <span class="ms-1 tabular-nums" :class="late(lane.next) ? 'text-ink-red-4' : 'text-ink-gray-5'">{{ shortDate(lane.next.due) }}</span>
            </div>
          </div>
          <div class="text-end text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [lane.done, lane.milestones.length]) }}</div>
        </div>
      </div>
    </div>
    <Rows class="md:hidden" :rows="phone" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Tooltip } from "frappe-ui";

import { Rows, __, go, shortDate, shortMonth, today } from "../kit";

const props = defineProps({ lanes: { type: Array, required: true } });
const emit = defineEmits(["main"]);

const DAY = 86400000;
const time = (day) => Date.parse(`${day}T00:00:00Z`);
const todayIs = today();

const span = computed(() => {
  const days = props.lanes.flatMap((lane) => lane.milestones.map((one) => one.due).filter(Boolean)).concat([todayIs]).map(time);
  const first = Math.min(...days) - 4 * DAY;
  const last = Math.max(...days) + 4 * DAY;
  return { first, last, width: last - first || DAY };
});
const at = (day) => (100 * (time(day) - span.value.first)) / span.value.width;
const now = computed(() => at(todayIs));

const ticks = computed(() => {
  const found = [];
  const start = new Date(span.value.first);
  let month = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1));
  while (month.getTime() <= span.value.last) {
    const day = month.toISOString().slice(0, 10);
    found.push({ day, at: at(day), label: shortMonth(day) });
    month = new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth() + 1, 1));
  }
  return found;
});

const rows = computed(() =>
  props.lanes.map((lane) => {
    const dated = lane.milestones.filter((one) => one.due).map((one) => ({ ...one, at: at(one.due) }));
    const next = dated.find((one) => !one.done) || lane.milestones.find((one) => !one.done) || null;
    return { ...lane, main: !lane.title, title: lane.title || __("Main", null, "Project"), dated, next };
  })
);

const late = (one) => !one.done && one.days !== null && one.days < 0;
const ring = (one, lane) =>
  one.done ? "border-outline-gray-5 bg-surface-gray-7" : late(one) ? "border-outline-red-3 bg-surface-red-5" : one.name === lane.next?.name ? "border-outline-gray-5 bg-surface-base" : "border-outline-gray-3 bg-surface-base";
const tip = (one) => [one.subject, one.in_lane, one.due ? shortDate(one.due) : __("No date")].filter(Boolean).join(" · ");

const openLane = (lane) => (lane.main ? emit("main") : go(`/desk/project/${encodeURIComponent(lane.key)}`));

const phone = computed(() =>
  rows.value.map((lane) => ({
    key: lane.key,
    label: lane.title,
    lines: [lane.next ? [lane.next.subject, lane.next.due ? shortDate(lane.next.due) : __("No date")].join(" · ") : __("Done")],
    value: __("{0} of {1}", [lane.done, lane.milestones.length]),
    dot: lane.next && late(lane.next) ? "red" : undefined,
    onClick: () => openLane(lane),
  }))
);
</script>
