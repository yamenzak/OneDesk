<template>
  <!-- Who is on the project: its members, its manager, and whoever its tasks
       are assigned to or logged time on it, with what's on them and what
       they've put in (one_project/team.py). -->
  <div class="pb-12">
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
              <Tooltip v-if="said.can_change && item.member" :text="__('Remove Member')">
                <Button variant="ghost" size="sm" icon="lucide-user-minus" :aria-label="__('Remove {0}', [item.name])" @click="removeMember(item)" />
              </Tooltip>
              <Tooltip v-else-if="said.can_change && item.can_join" :text="__('Make Member')">
                <Button variant="ghost" size="sm" icon="lucide-user-plus" :aria-label="__('Make {0} a member', [item.name])" @click="makeMember(item)" />
              </Tooltip>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>

      <section class="mt-8">
        <div class="mb-3 flex items-center gap-2">
          <h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Contacts") }}</h2>
          <Button v-if="outside?.can_change" class="ms-auto" size="sm" icon-left="lucide-plus" :label="__('Add Contact')" @click="contact()" />
        </div>
        <div v-if="!outside?.contacts.length" class="py-3 text-base text-ink-gray-5">{{ __("No contacts") }}</div>
        <List v-else :columns="{ base: ['minmax(0,1fr)', 'auto'], md: ['minmax(12rem,1.4fr)', '11rem', 'minmax(10rem,1fr)', '9rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
          <ListHeader>
            <ListHeaderCell>{{ __("Contact") }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Role") }}</ListHeaderCell>
            <ListHeaderCell class="max-md:hidden">{{ __("Email") }}</ListHeaderCell>
            <ListHeaderCell class="max-md:hidden">{{ __("Phone") }}</ListHeaderCell>
          </ListHeader>
          <ListRows :items="outside.contacts" row-key="row" v-slot="{ item }">
            <ListRow v-bind="outside.can_change ? { onClick: () => contact(item) } : {}">
              <ListCell class="min-w-0 gap-2.5">
                <Avatar :label="item.person || item.company" :image="item.image" :shape="item.person ? 'circle' : 'square'" size="md" />
                <div class="min-w-0">
                  <div class="truncate text-base text-ink-gray-8">{{ item.person || item.company }}</div>
                  <div class="truncate text-sm text-ink-gray-5">{{ [item.person ? item.company : "", item.note].filter(Boolean).join(" · ") }}</div>
                </div>
              </ListCell>
              <ListCell><Badge :label="__(item.role)" theme="gray" size="md" /></ListCell>
              <ListCell class="min-w-0 max-md:hidden">
                <a v-if="item.email" class="truncate text-ink-gray-7 hover:underline" :href="`mailto:${item.email}`" @click.stop>{{ item.email }}</a>
              </ListCell>
              <ListCell class="min-w-0 max-md:hidden">
                <a v-if="item.phone" class="truncate tabular-nums text-ink-gray-7 hover:underline" :href="`tel:${item.phone}`" @click.stop>{{ item.phone }}</a>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { Avatar, Badge, Button, Tooltip } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Loading, __, call, confirm, hours, onedesk } from "../kit";
import { onlyArg, useOnly } from "./only";

const props = defineProps({ projectName: { type: String, required: true }, modified: String });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();
const emit = defineEmits(["changed"]);
const said = ref(null);

// Who outside the company is on it (one_project/contacts.py).
const outside = ref(null);
async function load() {
  [said.value, outside.value] = await Promise.all([
    call("onedesk.one_project.team.team", { project: props.projectName, ...onlyArg(only) }),
    call("onedesk.one_project.contacts.contacts", { project: props.projectName }),
  ]);
}
const contact = (row) =>
  onedesk().project.contact(props.projectName, row || null, (now) => {
    outside.value = now;
    emit("changed");
  });
// A member added or taken off changes the project, which the page follows.
watch(() => [props.projectName, props.modified], load, { immediate: true });

const addMember = () =>
  onedesk().project.add_member({ doctype: "Project", doc: { name: props.projectName } }, (now) => {
    said.value = now;
    emit("changed");
  });
async function makeMember(person) {
  said.value = await call("onedesk.one_project.team.add", { project: props.projectName, user: person.user });
  emit("changed");
}
function removeMember(person) {
  confirm(__("Remove {0} from the project?", [person.name]), async () => {
    said.value = await call("onedesk.one_project.team.remove", { project: props.projectName, user: person.user });
    emit("changed");
  });
}
</script>
