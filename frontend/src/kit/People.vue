<template>
  <Dropdown v-if="options" :options="choices">
    <template #trigger>
      <button class="flex items-center rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="__('Assign')">
        <Stack :users="users" :people="people" :size="size" />
        <span v-if="!users.length" class="lucide-user-plus size-4 text-ink-gray-4" />
        <span v-else-if="named" class="ms-2 truncate text-base text-ink-gray-8">{{ names }}</span>
      </button>
    </template>
  </Dropdown>
  <span v-else class="flex min-w-0 items-center">
    <Stack :users="users" :people="people" :size="size" />
    <span v-if="named && users.length" class="ms-2 truncate text-base text-ink-gray-8">{{ names }}</span>
  </span>
</template>

<script setup>
import { computed, defineComponent, h } from "vue";
import { Avatar, Dropdown, Tooltip } from "frappe-ui";

import { __ } from "./desk";

const props = defineProps({
  users: { type: Array, default: () => [] },
  people: { type: Object, default: () => ({}) },
  options: Array,
  size: { type: String, default: "sm" },
  max: { type: Number, default: 3 },
  groups: { type: Array, default: () => [] },
  named: Boolean,
});
const emit = defineEmits(["add", "remove", "group"]);
const names = computed(() => props.users.map((user) => props.people[user]?.name || user).join(", "));

const Stack = defineComponent({
  props: ["users", "people", "size"],
  setup(stack) {
    return () =>
      h(
        "span",
        { class: "flex -space-x-1" },
        [
          ...stack.users.slice(0, props.max).map((user) => {
            const one = stack.people[user] || { name: user };
            return h(Tooltip, { text: one.name }, () =>
              h(Avatar, { label: one.name, image: one.image, size: stack.size, class: "ring-2 ring-outline-base" })
            );
          }),
          stack.users.length > props.max &&
            h(Avatar, { label: "+", size: stack.size, class: "ring-2 ring-outline-base" }, () =>
              h("span", { class: "text-xs font-medium normal-case tabular-nums" }, `+${stack.users.length - props.max}`)
            ),
        ].filter(Boolean)
      );
  },
});

const choices = computed(() => {
  const people = (props.options || []).map((user) => {
    const on = props.users.includes(user);
    return {
      label: props.people[user]?.name || user,
      selected: on,
      onClick: () => emit(on ? "remove" : "add", user),
    };
  });
  const groups = props.groups.filter((one) => one.users.some((user) => !props.users.includes(user)));
  if (!groups.length) return people;
  return [
    { group: __("People"), hideLabel: true, options: people },
    {
      group: __("Groups"),
      options: groups.map((one) => ({
        label: one.name,
        icon: "lucide-users",
        onClick: () => emit("group", one.users.filter((user) => !props.users.includes(user))),
      })),
    },
  ];
});
</script>
