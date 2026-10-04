<template>
  <!-- People on something, as overlapping avatars; with `options`, clicking
       picks who, each one ticked on or off. -->
  <Dropdown v-if="options" :options="choices">
    <template #trigger>
      <button class="flex items-center rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="__('Assign')">
        <Stack :users="users" :people="people" :size="size" />
        <span v-if="!users.length" class="lucide-user-plus size-4 text-ink-gray-4" />
      </button>
    </template>
  </Dropdown>
  <Stack v-else :users="users" :people="people" :size="size" />
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
});
const emit = defineEmits(["add", "remove"]);

const Stack = defineComponent({
  props: ["users", "people", "size"],
  setup(stack) {
    return () =>
      h(
        "span",
        { class: "flex -space-x-1.5" },
        stack.users.slice(0, props.max).map((user) => {
          const one = stack.people[user] || { name: user };
          return h(Tooltip, { text: one.name }, () =>
            h(Avatar, { label: one.name, image: one.image, size: stack.size, class: "ring-2 ring-outline-gray-1" })
          );
        })
      );
  },
});

const choices = computed(() =>
  (props.options || []).map((user) => {
    const on = props.users.includes(user);
    return {
      label: props.people[user]?.name || user,
      selected: on,
      onClick: () => emit(on ? "remove" : "add", user),
    };
  })
);
</script>
