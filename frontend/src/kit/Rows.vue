<template>
  <!-- Rows of a list: frappe-ui's List. A row says what it is, a quiet aside,
       a quieter `sub` after the name, shown whole or left out when the row is narrow,
       a badge after the name (a label, or `{ label, theme }`), a line or lines under the name (`below`, `lines`), a bar of how far along it is (the
       aside then goes under the name; with
       `then`, a lighter part after it, drawn as frappe-ui's Progress), and a
       value on the right (with a quieter `under` it); it may carry a
       dot or an avatar (`avatar` the name, `image` the picture, or an
       `icon` in its place), and
       opens its `route` or runs its `onClick`. A row's `actions` are a menu
       at its end, frappe-ui's Dropdown. -->
  <div v-if="!rows.length && empty" class="py-3 text-base text-ink-gray-5">{{ empty }}</div>
  <List v-else :columns="columns" :row-height="height" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
    <ListRows :items="rows" row-key="key" v-slot="{ item }">
      <ListRow v-bind="opens(item)">
        <ListCell class="min-w-0 gap-2.5">
          <span v-if="item.dot" class="h-2 w-2 shrink-0 rounded-full" :class="dots[item.dot] || dots.gray" />
          <Avatar v-if="item.avatar" :label="item.avatar" :image="item.image" :shape="item.square ? 'square' : 'circle'" size="sm" />
          <Avatar v-else-if="item.icon" :shape="item.square ? 'square' : 'circle'" size="sm"><span :class="item.icon" class="size-3" /></Avatar>
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 items-center gap-2">
              <div class="flex h-[1lh] min-w-0 flex-wrap overflow-hidden text-base">
                <span class="max-w-full truncate text-ink-gray-8">{{ item.label }}</span>
                <span v-if="item.sub" class="whitespace-nowrap ps-1 text-ink-gray-5">· {{ item.sub }}</span>
              </div>
              <Badge v-if="item.badge" :label="item.badge.label || item.badge" :theme="item.badge.theme || 'gray'" size="sm" />
            </div>
            <div v-if="bars && item.dim" class="truncate text-sm tabular-nums text-ink-gray-5">{{ item.dim }}</div>
            <div v-if="item.below" class="truncate text-sm text-ink-gray-5">{{ item.below }}</div>
            <div v-for="(line, i) in item.lines || []" :key="i" class="truncate text-sm text-ink-gray-5">{{ line }}</div>
          </div>
        </ListCell>
        <ListCell v-if="bars">
          <div v-if="item.then" class="flex h-1 w-full gap-[2px] overflow-hidden rounded-7" role="img" :aria-label="item.dim">
            <div v-if="item.progress" class="bg-surface-gray-10" :style="{ width: `${item.progress}%` }" />
            <div class="bg-surface-gray-5" :style="{ width: `${item.then}%` }" />
            <div class="flex-1 bg-surface-gray-2" />
          </div>
          <Progress v-else-if="item.progress !== undefined && item.progress !== null" :value="item.progress" size="md" class="w-full" />
        </ListCell>
        <ListCell v-else-if="dims" class="justify-end text-base tabular-nums text-ink-gray-5">{{ item.dim }}</ListCell>
        <ListCell v-if="values" class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-7">
          <div class="text-end">
            <div>{{ item.value }}</div>
            <div v-if="item.under" class="text-sm text-ink-gray-5">{{ item.under }}</div>
          </div>
        </ListCell>
        <ListCell v-if="menus" class="justify-end" @click.stop>
          <Dropdown v-if="item.actions?.length" :options="item.actions" placement="right">
            <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Badge, Button, Dropdown, Progress } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import { __, go } from "./desk";

const props = defineProps({ rows: { type: Array, required: true }, empty: String });
const bars = computed(() => props.rows.some((row) => row.progress !== undefined && row.progress !== null));
const menus = computed(() => props.rows.some((row) => row.actions?.length));
// A column for the aside and one for the value, each only when some row has one.
const dims = computed(() => props.rows.some((row) => row.dim));
const values = computed(() => props.rows.some((row) => row.value || row.under));
const columns = computed(() => [
  "minmax(0,1fr)",
  ...(bars.value ? ["6rem"] : dims.value ? ["auto"] : []),
  ...(values.value ? ["minmax(8rem,max-content)"] : []),
  ...(menus.value ? ["2rem"] : []),
]);
// One line for the name, and one more for each line under it.
const height = computed(() =>
  Math.max(...props.rows.map((row) => 40 + 18 * Math.max((bars.value && row.dim ? 1 : 0) + (row.below ? 1 : 0) + (row.lines?.length || 0), row.under ? 1 : 0)), 40)
);

const dots = { red: "bg-surface-red-5", amber: "bg-surface-amber-5", orange: "bg-surface-amber-5", green: "bg-surface-green-5", blue: "bg-surface-blue-5", gray: "bg-surface-gray-5" };

function opens(item) {
  if (item.onClick) return { onClick: item.onClick };
  if (item.route) return { onClick: () => go(item.route) };
  return {};
}
</script>
