<template>
  <div class="overflow-x-auto rounded-5 border border-outline-gray-2">
    <List :columns="COLUMNS" :row-height="44" divider="full" class="min-w-[40rem] list-gap-3 list-row-px-3">
      <ListHeader class="bg-surface-gray-1">
        <ListHeaderCell>{{ __("Task") }}</ListHeaderCell>
        <ListHeaderCell>{{ __("When") }}</ListHeaderCell>
        <ListHeaderCell>{{ __("Depends On") }}</ListHeaderCell>
        <ListHeaderCell>{{ __("Hours") }}</ListHeaderCell>
        <ListHeaderCell />
      </ListHeader>
      <ListRows :items="rows" row-key="name" v-slot="{ item }">
        <ListRow>
          <ListCell class="min-w-0 gap-1.5" :style="item.depth ? { paddingInlineStart: `${item.depth * 1.25}rem` } : null">
            <span v-if="item.depth" class="lucide-corner-down-right size-4 shrink-0 text-ink-gray-4" />
            <Button
              v-if="canWrite"
              size="sm"
              icon="lucide-flag"
              :theme="item.is_milestone ? 'blue' : 'gray'"
              :variant="item.is_milestone ? 'subtle' : 'ghost'"
              :class="!item.is_milestone && 'opacity-40 hover:opacity-100'"
              :aria-label="item.is_milestone ? __('Not a Milestone') : __('Milestone')"
              :aria-pressed="!!item.is_milestone"
              @click="$emit('change', item.name, 'is_milestone', item.is_milestone ? 0 : 1)"
            />
            <span v-else-if="item.is_milestone" class="lucide-flag size-4 shrink-0 text-ink-blue-5" :aria-label="__('Milestone')" />
            <TextInput
              v-if="canWrite"
              size="sm"
              variant="ghost"
              class="min-w-0 flex-1 [&_input]:truncate"
              :class="item.is_group && 'font-semibold'"
              :model-value="item.subject"
              :title="item.subject"
              :aria-label="__('Task')"
              @change="(e) => rename(item, e.target.value)"
            />
            <span v-else class="min-w-0 flex-1 truncate text-base text-ink-gray-8" :class="item.is_group && 'font-semibold'">{{ item.subject }}</span>
          </ListCell>
          <ListCell>
            <Popover v-if="canWrite">
              <template #trigger>
                <Button size="sm" variant="ghost" :label="when(item)" />
              </template>
              <template #default>
                <div class="flex w-56 flex-col gap-3 p-3">
                  <TextInput type="number" size="sm" min="0" :label="__('Begin On (Days)')" :model-value="item.start" @change="(e) => $emit('change', item.name, 'start', e.target.value)" />
                  <TextInput type="number" size="sm" min="0" :label="__('Duration (Days)')" :model-value="item.duration" @change="(e) => $emit('change', item.name, 'duration', e.target.value)" />
                </div>
              </template>
            </Popover>
            <span v-else class="text-base tabular-nums text-ink-gray-7">{{ when(item) }}</span>
          </ListCell>
          <ListCell class="min-w-0 gap-1">
            <Badge v-for="one in item.waits" :key="one" theme="gray" class="min-w-0">
              <span class="max-w-32 truncate">{{ subject(one) }}</span>
              <template v-if="canWrite" #suffix>
                <button class="lucide-x size-3" :aria-label="__('Stop Waiting on {0}', [subject(one)])" @click="$emit('wait', item.name, one, 0)" />
              </template>
            </Badge>
            <Dropdown v-if="canWrite && others(item).length" :options="others(item)">
              <template #trigger>
                <Button size="sm" variant="ghost" icon="lucide-plus" :aria-label="__('Wait On')" />
              </template>
            </Dropdown>
          </ListCell>
          <ListCell>
            <TextInput
              v-if="canWrite"
              type="number"
              size="sm"
              variant="ghost"
              min="0"
              step="0.5"
              class="w-16 tabular-nums"
              :model-value="item.expected_time || ''"
              :aria-label="__('Expected Time')"
              placeholder="–"
              @change="(e) => $emit('change', item.name, 'expected_time', e.target.value)"
            />
            <span v-else class="text-base tabular-nums" :class="item.expected_time ? 'text-ink-gray-7' : 'text-ink-gray-4'">{{ item.expected_time || "–" }}</span>
          </ListCell>
          <ListCell>
            <Dropdown v-if="canWrite" :options="menu(item)">
              <template #trigger>
                <Button size="sm" variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" />
              </template>
            </Dropdown>
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
    <div v-if="canWrite" class="flex items-center gap-2 border-t border-outline-gray-1 px-3 py-1.5">
      <span class="lucide-plus size-4 text-ink-gray-4" />
      <input
        v-model="draft"
        class="w-full border-0 bg-transparent p-1 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-0"
        :placeholder="__('Add Task')"
        @keydown.enter="add"
      />
    </div>
    <div v-else-if="!rows.length" class="border-t border-outline-gray-1 px-3 py-3 text-base text-ink-gray-5">{{ __("No tasks") }}</div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Badge, Button, Dropdown, Popover, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __ } from "../kit";

const props = defineProps({
  tasks: { type: Array, required: true },
  canWrite: Boolean,
});
const emit = defineEmits(["change", "add", "nest", "wait", "remove", "under"]);

const COLUMNS = ["minmax(14rem,1fr)", "8.5rem", "minmax(7rem,12rem)", "4.5rem", "2.5rem"];
const rows = computed(() => props.tasks);
const names = computed(() => Object.fromEntries(props.tasks.map((one) => [one.name, one.subject])));
const subject = (name) => names.value[name] || name;
const draft = ref("");

const when = (one) =>
  `${__("Day {0}", [one.start || 0])} · ${one.duration === 1 ? __("1 day") : __("{0} days", [one.duration || 0])}`;

function rename(one, value) {
  const now = (value || "").trim();
  if (now && now !== one.subject) emit("change", one.name, "subject", now);
}

function add() {
  const now = draft.value.trim();
  if (!now) return;
  draft.value = "";
  emit("add", now, null);
}

function below(one) {
  const under = new Set([one.name]);
  for (const other of props.tasks) if (under.has(other.parent_task)) under.add(other.name);
  return under;
}

const others = (one) =>
  props.tasks
    .filter((other) => other.name !== one.name && !one.waits.includes(other.name) && other.parent_task !== one.name)
    .map((other) => ({ label: other.subject, onClick: () => emit("wait", one.name, other.name, 1) }));

function menu(one) {
  const mine = below(one);
  const parents = props.tasks
    .filter((other) => !mine.has(other.name) && other.name !== one.parent_task)
    .map((other) => ({ label: other.subject, onClick: () => emit("nest", one.name, other.name) }));
  return [
    { label: __("Add Task Under"), icon: "lucide-list-plus", onClick: () => emit("under", one.name) },
    parents.length && { label: __("Put Under"), icon: "lucide-corner-down-right", submenu: parents },
    one.parent_task && { label: __("Move to the Top"), icon: "lucide-corner-left-up", onClick: () => emit("nest", one.name, null) },
    { label: __("Delete"), icon: "lucide-trash-2", theme: "red", onClick: () => emit("remove", one.name) },
  ].filter(Boolean);
}
</script>
