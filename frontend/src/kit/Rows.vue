<template>
  <!-- Rows of a list: frappe-ui's List. A row says what it is, a quiet aside,
       a bar of how far along it is (the aside then goes under the name), and a
       value on the right; it may carry a
       dot or an avatar, and
       opens its `route` or runs its `onClick`. -->
  <div v-if="!rows.length && empty" class="py-3 text-base text-ink-gray-5">{{ empty }}</div>
  <List v-else :columns="['minmax(0,1fr)', bars ? '6rem' : 'auto', '8rem']" :row-height="bars ? 48 : 40" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
    <ListRows :items="rows" row-key="key" v-slot="{ item }">
      <ListRow v-bind="opens(item)">
        <ListCell class="min-w-0 gap-2.5">
          <span v-if="item.dot" class="h-2 w-2 shrink-0 rounded-full" :class="dots[item.dot] || dots.gray" />
          <Avatar v-if="item.avatar" :label="item.avatar" size="sm" />
          <div class="min-w-0 flex-1">
            <div class="truncate text-base text-ink-gray-8">
              {{ item.label }}<span v-if="item.sub" class="text-ink-gray-5"> · {{ item.sub }}</span>
            </div>
            <div v-if="bars && item.dim" class="truncate text-sm tabular-nums text-ink-gray-5">{{ item.dim }}</div>
          </div>
        </ListCell>
        <ListCell v-if="bars"><Progress v-if="item.progress !== undefined && item.progress !== null" :value="item.progress" size="md" class="w-full" /></ListCell>
        <ListCell v-else class="justify-end text-base tabular-nums text-ink-gray-5">{{ item.dim }}</ListCell>
        <ListCell class="justify-end text-base tabular-nums text-ink-gray-7">{{ item.value }}</ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Progress } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import { go } from "./desk";

const props = defineProps({ rows: { type: Array, required: true }, empty: String });
const bars = computed(() => props.rows.some((row) => row.progress !== undefined && row.progress !== null));

const dots = { red: "bg-surface-red-5", orange: "bg-surface-amber-5", green: "bg-surface-green-5", blue: "bg-surface-blue-5", gray: "bg-surface-gray-5" };

function opens(item) {
  if (item.onClick) return { onClick: item.onClick };
  if (item.route) return { onClick: () => go(item.route) };
  return {};
}
</script>
