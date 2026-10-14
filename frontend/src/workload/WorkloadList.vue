<template>
  <!-- Workload (one_project/report/workload): who has how many hours of open
       work in a week, against the hours they have. Modelled on Asana's
       Workload and Float's capacity view: the team's week in one line with
       a bar, then a row a person, their load as a bar that turns red past
       what they have, the hours planned of the hours free, and their tasks,
       late and not estimated, each opening the tasks it counts. -->
  <div class="mx-auto w-full px-5 pb-16 pt-4 text-ink-gray-8">
    <div class="rounded-4 border border-outline-gray-1 bg-surface-elevation-2 p-5">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ __("{0} of {1} planned", [hours(planned), hours(capacity)]) }}</h2>
        <span class="text-sm" :class="over ? 'text-ink-red-5' : 'text-ink-gray-5'">
          {{ over ? (over === 1 ? __("1 person over capacity") : __("{0} people over capacity", [count(over)])) : __("Everyone has room") }}
        </span>
      </div>
      <Progress :value="capacity ? Math.min(100, Math.round((100 * planned) / capacity)) : 0" size="md" class="mt-3" />
      <p v-if="week" class="mt-2 text-sm text-ink-gray-5">{{ week }}</p>
    </div>

    <p v-if="!rows.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nobody has work this week") }}</p>
    <List v-else :columns="columns" divider="full" :row-height="60" class="mt-4 list-gap-4 list-row-px-3">
      <ListHeader>
        <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
        <ListHeaderCell>{{ __("Load") }}</ListHeaderCell>
        <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Planned") }}</ListHeaderCell>
        <ListHeaderCell class="justify-end max-md:hidden">{{ __("Free") }}</ListHeaderCell>
      </ListHeader>
      <ListRows :items="rows" row-key="user" v-slot="{ item }">
        <ListRow @click="onOpen?.(item.user, 'tasks')">
          <ListCell class="min-w-0 gap-3">
            <Avatar :label="item.full_name || item.user" :image="item.image" size="lg" />
            <div class="flex min-w-0 flex-col gap-1">
              <span class="truncate text-base font-medium text-ink-gray-8">{{ item.full_name || item.user }}</span>
              <span class="flex min-w-0 items-center gap-1.5 truncate text-sm text-ink-gray-5" @click.stop>
                <button v-if="item.tasks" class="hover:underline" @click="onOpen?.(item.user, 'tasks')">{{ item.tasks === 1 ? __("1 task") : __("{0} tasks", [count(item.tasks)]) }}</button>
                <span v-else>{{ __("No tasks") }}</span>
                <template v-if="item.late">
                  <span aria-hidden="true">·</span>
                  <button class="text-ink-red-5 hover:underline" @click="onOpen?.(item.user, 'late')">{{ __("{0} late", [count(item.late)]) }}</button>
                </template>
                <template v-if="item.unestimated">
                  <span aria-hidden="true">·</span>
                  <button class="hover:underline" @click="onOpen?.(item.user, 'unestimated')">{{ __("{0} not estimated", [count(item.unestimated)]) }}</button>
                </template>
              </span>
            </div>
          </ListCell>
          <ListCell>
            <div class="flex w-full items-center gap-3">
              <div class="h-2 flex-1 overflow-hidden rounded-full bg-surface-gray-2" role="meter" :aria-valuenow="item.load || 0" aria-valuemin="0" aria-valuemax="100" :aria-label="__('Load')">
                <div class="h-full rounded-full" :class="tone(item)" :style="{ width: `${Math.min(100, item.load || 0)}%` }" />
              </div>
              <span class="w-12 text-end text-base tabular-nums" :class="(item.load || 0) > 100 ? 'text-ink-red-5 font-medium' : 'text-ink-gray-7'">{{ item.load === null ? "–" : `${item.load}%` }}</span>
            </div>
          </ListCell>
          <ListCell class="justify-end whitespace-nowrap tabular-nums max-sm:hidden">
            <span class="text-base text-ink-gray-8">{{ hours(item.planned) }}</span>
            <span class="ms-1 text-sm text-ink-gray-5">{{ __("of {0}", [hours(item.capacity)]) }}</span>
          </ListCell>
          <ListCell class="justify-end whitespace-nowrap text-base tabular-nums max-md:hidden" :class="item.free < 0 ? 'text-ink-red-5' : 'text-ink-gray-7'">
            {{ hours(item.free) }}
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, count, hours } from "../kit";

const props = defineProps({ rows: { type: Array, default: () => [] }, week: String, onOpen: Function });

const capacity = computed(() => props.rows.reduce((sum, one) => sum + (one.capacity || 0), 0));
const planned = computed(() => props.rows.reduce((sum, one) => sum + (one.planned || 0), 0));
const over = computed(() => props.rows.filter((one) => (one.load || 0) > 100).length);

// The load is the one a phone keeps beside the person; the hours join as it widens.
const columns = {
  base: ["minmax(0,1fr)", "9rem"],
  sm: ["minmax(0,1fr)", "minmax(9rem,16rem)", "8rem"],
  md: ["minmax(0,1fr)", "minmax(10rem,20rem)", "8rem", "6rem"],
};

// Over what they have in red, nearly full in amber, the rest in the bar's own colour.
const tone = (one) => ((one.load || 0) > 100 ? "bg-surface-red-5" : (one.load || 0) >= 85 ? "bg-surface-amber-5" : "bg-surface-gray-7");
</script>
