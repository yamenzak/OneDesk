<template>
  <!-- Who is on the project: its members, its manager, and whoever its tasks
       are assigned to or logged time on it, with what's on them and what
       they've put in (one_project/team.py). -->
  <div class="pb-12">
    <Loading v-if="!said" />
    <template v-else>
      <!-- The title and what can be done, on one line as on the other views. -->
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
          <span class="lucide-users size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Team") }}
          <span v-if="said.people.length" class="text-base font-normal text-ink-gray-5">{{ said.people.length }}</span>
        </h2>
        <Button v-if="said.can_change" size="sm" variant="solid" icon-left="lucide-user-plus" :label="__('Add User')" @click="addMember" />
      </div>
      <!-- What the workspace's extensions add here (one_studio/places.py). -->
      <PlaceSpot :said="spot" class="mb-4" />
      <div v-if="!said.people.length" class="flex flex-col items-center gap-3 py-16 text-center">
        <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-users size-5" /></span>
        <p class="text-base text-ink-gray-7">{{ __("No one yet") }}</p>
      </div>
      <List v-else :columns="{ base: ['minmax(0,1fr)', '7rem', '2rem'], md: ['minmax(12rem,1.6fr)', '8rem', '6.5rem', '6.5rem', '2rem'] }" :row-height="52" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Person") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Open Tasks") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("This Month") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("All Time") }}</ListHeaderCell>
          <ListHeaderCell />
        </ListHeader>
        <ListRows :items="said.people" row-key="user" v-slot="{ item }">
          <ListRow>
            <ListCell class="min-w-0 gap-2.5">
              <Avatar :label="item.name" :image="item.image" size="md" />
              <div class="min-w-0">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
                  <Badge v-if="item.manager" :label="__('Manager')" theme="blue" size="md" />
                  <Badge v-else-if="item.member" :label="__('User')" theme="gray" size="md" />
                </div>
                <div v-if="item.job || !item.signs_in || item.portal" class="truncate text-sm text-ink-gray-5">{{ [item.job, !item.signs_in && __("No sign-in"), item.portal && __("Portal")].filter(Boolean).join(" · ") }}</div>
              </div>
            </ListCell>
            <!-- Open tasks, and how many of them are late. -->
            <ListCell class="justify-end gap-1 tabular-nums text-ink-gray-7">
              <template v-if="item.open">{{ item.open }}<span v-if="item.late" class="text-ink-red-5"> · {{ __("{0} late", [item.late]) }}</span></template>
              <template v-else>–</template>
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ item.month ? hours(item.month) : "–" }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ item.hours ? hours(item.hours) : "–" }}</ListCell>
            <ListCell class="justify-end">
              <Dropdown v-if="actions(item).length" :options="actions(item)" placement="right">
                <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
              </Dropdown>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>

      <section class="mt-8">
        <div class="mb-3 flex items-center gap-2">
          <h2 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
            <span class="lucide-contact size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Contacts") }}
            <span v-if="outside?.contacts.length" class="text-base font-normal text-ink-gray-5">{{ outside.contacts.length }}</span>
          </h2>
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
import { onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Loading, PlaceSpot, __, call, confirm, followList, hours, onedesk } from "../kit";
import { onlyArg, useOnly } from "./only";
import { usePlace } from "./place";

const props = defineProps({ projectName: { type: String, required: true }, modified: String });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();
const emit = defineEmits(["changed"]);
const said = ref(null);

// Who outside the company is on it (one_project/contacts.py).
const outside = ref(null);
const spot = usePlace("oneproject.team", () =>
  said.value && {
    project: { name: props.projectName },
    team: { people: said.value.people.length, contacts: outside.value?.contacts?.length || 0 },
  }
);
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
// A member added or taken off changes the project, which the page follows;
// a task or time changes a person's counts.
watch(() => [props.projectName, props.modified], load, { immediate: true });
let timer = null;
const later = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
const stops = ["Task", "Timesheet", "Contact"].map((doctype) => followList(doctype, later));
onBeforeUnmount(() => {
  stops.forEach((stop) => stop());
  clearTimeout(timer);
});

const addMember = () =>
  onedesk().project.add_member({ doctype: "Project", doc: { name: props.projectName } }, (now) => {
    said.value = now;
    emit("changed");
  });
async function makeMember(person) {
  said.value = await call("onedesk.one_project.team.add", { project: props.projectName, user: person.user });
  emit("changed");
}
// What a member who signs in on the portal sees of the project there.
async function show(person, what) {
  said.value = await call("onedesk.one_project.team.show", { project: props.projectName, user: person.user, ...what });
  emit("changed");
}
// Make Member, or Remove Member: their tasks and time stay either way.
function actions(person) {
  if (!said.value.can_change) return [];
  if (person.member)
    return [
      ...(person.portal
        ? [
            person.timesheets
              ? { label: __("Hide Timesheets"), icon: "lucide-eye-off", onClick: () => show(person, { timesheets: 0 }) }
              : { label: __("Show Timesheets"), icon: "lucide-eye", onClick: () => show(person, { timesheets: 1 }) },
            person.files
              ? { label: __("Hide Files"), icon: "lucide-eye-off", onClick: () => show(person, { files: 0 }) }
              : { label: __("Show Files"), icon: "lucide-eye", onClick: () => show(person, { files: 1 }) },
          ]
        : []),
      { label: __("Remove User"), icon: "lucide-user-minus", onClick: () => removeMember(person) },
    ];
  if (person.can_join) return [{ label: __("Add to Users"), icon: "lucide-user-plus", onClick: () => makeMember(person) }];
  return [];
}
function removeMember(person) {
  confirm(__("Remove {0} from the project?", [person.name]), async () => {
    said.value = await call("onedesk.one_project.team.remove", { project: props.projectName, user: person.user });
    emit("changed");
  });
}
</script>
