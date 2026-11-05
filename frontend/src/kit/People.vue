<template>
  <span class="flex -space-x-1">
    <Tooltip v-for="user in users.slice(0, max)" :key="user" :text="(people[user] || { name: user }).name">
      <Avatar :label="(people[user] || { name: user }).name" :image="people[user]?.image" :size="size" class="ring-2 ring-outline-base" />
    </Tooltip>
    <Avatar v-if="users.length > max" label="+" :size="size" class="ring-2 ring-outline-base">
      <span class="text-xs font-medium normal-case tabular-nums">+{{ users.length - max }}</span>
    </Avatar>
  </span>
</template>

<script setup>
import { Avatar, Tooltip } from "frappe-ui";

defineProps({
  users: { type: Array, default: () => [] },
  people: { type: Object, default: () => ({}) },
  size: { type: String, default: "sm" },
  max: { type: Number, default: 3 },
});
</script>
