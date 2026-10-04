<template>
  <!-- Who is on the project: its members, its manager, and whoever its tasks
       are assigned to or logged time on it, with what's on them and what
       they've put in (one_project/team.py). -->
  <div class="pb-12 pt-4">
    <Loading v-if="!said" />
    <template v-else>
      <div class="mb-3 flex items-center gap-2">
        <span class="text-base text-ink-gray-6">{{ said.people.length === 1 ? __("1 person") : __("{0} people", [said.people.length]) }}</span>
        <Button v-if="said.can_change" class="ms-auto" size="sm" variant="solid" icon-left="lucide-user-plus" :label="__('Add Member')" @click="addMember" />
      </div>
      <div v-if="!said.people.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-users size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No one yet") }}</p>
      </div>
      <List v-else :columns="{ base: ['minmax(0,1fr)', '5.5rem', '2.5rem'], md: ['minmax(12rem,1.6fr)', '6rem', '5rem', '6.5rem', '6.5rem', '2.5rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Open Tasks") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Late") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("This Month") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("All Time") }}</ListHeaderCell>
          <ListHeaderCell />
        </ListHeader>
        <ListRows :items="said.people" row-key="user" v-slot="{ item }">
          <ListRow>
            <ListCell class="min-w-0 gap-2.5">
              <Avatar :label="item.name" :image="item.image" size="md" />
              <span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
              <Badge v-if="item.manager" :label="__('Manager')" theme="blue" size="md" />
              <Badge v-else-if="item.member" :label="__('Member')" theme="gray" size="md" />
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ item.open || "–" }}</ListCell>
            <ListCell class="justify-end tabular-nums max-md:hidden" :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ item.late || "–" }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ item.month ? hours(item.month) : "–" }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ item.hours ? hours(item.hours) : "–" }}</ListCell>
            <ListCell class="justify-end">
              <Button v-if="said.can_change && item.member" variant="ghost" size="sm" icon="lucide-user-minus" :aria-label="__('Remove {0}', [item.name])" @click="removeMember(item)" />
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { Avatar, Badge, Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Loading, __, call, confirm, hours, onedesk } from "../kit";

const props = defineProps({ projectName: { type: String, required: true }, modified: String });
const emit = defineEmits(["changed"]);
const said = ref(null);

async function load() {
  said.value = await call("onedesk.one_project.team.team", { project: props.projectName });
}
// A member added or taken off changes the project, which the page follows.
watch(() => [props.projectName, props.modified], load, { immediate: true });

const addMember = () =>
  onedesk().project.add_member({ doctype: "Project", doc: { name: props.projectName } }, (now) => {
    said.value = now;
    emit("changed");
  });
function removeMember(person) {
  confirm(__("Take {0} off the project?", [person.name]), async () => {
    said.value = await call("onedesk.one_project.team.remove", { project: props.projectName, user: person.user });
    emit("changed");
  });
}
</script>
