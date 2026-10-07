<template>
  <!-- Tasks as a table in groups, as monday's main table: every cell changes
       in place, and a row's name opens it beside the page. -->
  <div class="pb-12">
    <div v-for="group in groups" :key="group.key" class="mt-6">
      <div class="mb-2 flex items-center gap-2">
        <Button variant="ghost" size="sm" :icon="closed[group.key] ? 'lucide-chevron-right' : 'lucide-chevron-down'" :aria-label="closed[group.key] ? __('Expand') : __('Collapse')" @click="closed[group.key] = !closed[group.key]" />
        <span class="h-5 w-1 rounded-full" :class="group.bar" />
        <button v-if="group.route" class="text-lg font-semibold text-ink-gray-9 hover:underline" @click="go(group.route)">{{ group.title }}</button>
        <span v-else class="text-lg font-semibold text-ink-gray-9">{{ group.title }}</span>
        <span class="text-base text-ink-gray-5">{{ group.tasks.length }}</span>
        <span v-if="planned(group)" class="text-base text-ink-gray-5">· {{ hours(planned(group)) }}</span>
      </div>
      <div v-if="!closed[group.key]" class="overflow-x-auto rounded-5 border border-outline-gray-2">
        <List :columns="COLUMNS" :row-height="group.tasks.some((one) => one.waiting?.length) ? 58 : 44" divider="full" class="min-w-[58rem] list-gap-3 list-row-px-3">
          <ListHeader class="bg-surface-gray-1">
            <ListHeaderCell>{{ __("Task") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Owner") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Status") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Due") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Priority") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Hours") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Progress") }}</ListHeaderCell>
          </ListHeader>
          <ListRows :items="nest(group.tasks)" row-key="name" v-slot="{ item }">
            <ListRow>
              <ListCell class="min-w-0 gap-2" :style="item.depth ? { paddingInlineStart: `${item.depth * 1.25}rem` } : null">
                <span v-if="item.depth" class="lucide-corner-down-right size-4 shrink-0 text-ink-gray-4" />
                <span v-if="item.is_milestone" class="lucide-flag size-4 shrink-0 text-ink-gray-5" />
                <div class="min-w-0">
                  <div class="flex min-w-0 items-center gap-2">
                    <button data-task-open class="truncate text-start text-base text-ink-gray-8 hover:underline" :class="[item.status === 'Completed' && 'text-ink-gray-5 line-through', item.name === current && 'font-semibold underline']" @click="$emit('open', item.name)">{{ item.subject }}</button>
                    <span v-if="item.sub" class="shrink-0 text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [item.subDone, item.sub]) }}</span>
                  </div>
                  <div v-if="item.waiting?.length" class="truncate text-sm text-ink-amber-5">{{ __("Waiting on {0}", [item.waiting.join(", ")]) }}</div>
                </div>
              </ListCell>
              <ListCell>
                <People :users="item.assigned" :people="work.people" :options="canWrite ? team : null" :groups="canWrite ? work.user_groups || [] : []" @add="(u) => $emit('give', item.name, u)" @group="(users) => $emit('give', item.name, users)" @remove="(u) => $emit('take', item.name, u)" />
              </ListCell>
              <ListCell>
                <Pill :value="item.status" :options="work.statuses" :colors="TASK_STATUS" :label="__('Status')" :readonly="!canWrite" @change="(v) => $emit('set', item.name, 'status', v)" />
              </ListCell>
              <ListCell>
                <Due :value="item.exp_end_date" :done="DONE.includes(item.status)" :readonly="!canWrite" @change="(v) => $emit('set', item.name, 'exp_end_date', v)" />
              </ListCell>
              <ListCell>
                <Pill :value="item.priority" :options="work.priorities" :colors="PRIORITY" :label="__('Priority')" :readonly="!canWrite" @change="(v) => $emit('set', item.name, 'priority', v)" />
              </ListCell>
              <ListCell>
                <TextInput
                  type="number"
                  size="sm"
                  variant="ghost"
                  min="0"
                  step="0.5"
                  class="w-16 tabular-nums"
                  :model-value="item.expected_time || ''"
                  :disabled="!canWrite"
                  :aria-label="__('Hours')"
                  placeholder="–"
                  @change="(e) => $emit('set', item.name, 'expected_time', Number(e.target.value) || 0)"
                />
              </ListCell>
              <ListCell class="gap-2">
                <Progress :value="item.status === 'Completed' ? 100 : item.progress || 0" size="sm" class="w-16" />
                <span class="text-sm tabular-nums text-ink-gray-5">{{ item.status === 'Completed' ? 100 : Math.round(item.progress || 0) }}%</span>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
        <div v-if="work.can_create && group.project !== undefined" class="flex items-center gap-2 border-t border-outline-gray-1 px-3 py-1.5">
          <span class="lucide-plus size-4 text-ink-gray-4" />
          <input
            v-model="drafts[group.key]"
            class="w-full border-0 bg-transparent p-1 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-0"
            :placeholder="__('Add Task')"
            @keydown.enter="add(group)"
          />
        </div>
        <div v-else-if="!group.tasks.length" class="border-t border-outline-gray-1 px-3 py-3 text-base text-ink-gray-5">{{ __("No tasks") }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import { Button, Progress, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { People, Pill, __, go, hours } from "../kit";
import { DONE, PRIORITY, TASK_STATUS } from "./colors";
import Due from "./Due.vue";
import { nest } from "./group";

const props = defineProps({
  work: { type: Object, required: true },
  groups: { type: Array, required: true },
  team: { type: Array, default: () => [] },
  canWrite: Boolean,
  // The task open in the panel, marked in its row.
  current: String,
});
const emit = defineEmits(["open", "set", "give", "take", "add"]);

const COLUMNS = ["minmax(14rem,1fr)", "6rem", "9rem", "8rem", "7rem", "5rem", "8rem"];
// The hours planned for a group's tasks (ERPNext's Expected Time).
const planned = (group) => group.tasks.reduce((sum, one) => sum + (Number(one.expected_time) || 0), 0);
const closed = reactive({});
const drafts = reactive({});

function add(group) {
  const subject = (drafts[group.key] || "").trim();
  if (!subject) return;
  drafts[group.key] = "";
  emit("add", group.project, subject);
}
</script>
