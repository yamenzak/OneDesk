<template>
  <!-- A record's sidebar as its form has it: who has it open, who it is
       assigned to, its tags, who it is shared with, its likes, and who made
       and last changed it. `of` is useRecord's; each change is frappe's own. -->
  <div v-if="said" class="space-y-5 text-base">
    <div v-if="of.viewers.value.length" class="flex items-center gap-2">
      <People :users="of.viewers.value" :people="people" />
      <span class="text-sm text-ink-gray-5">{{ __("Currently Viewing") }}</span>
    </div>

    <div>
      <Head :label="__('Assigned To')" :add="can.assign ? of.assign : null" />
      <ul v-if="said.assigned.length" class="space-y-1.5">
        <li v-for="user in said.assigned" :key="user" class="group flex items-center gap-2">
          <Avatar :label="person(user).name" :image="person(user).image" size="sm" />
          <span class="min-w-0 flex-1 truncate text-ink-gray-8">{{ person(user).name }}</span>
          <Button v-if="can.assign" variant="ghost" size="sm" icon="lucide-x" class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100" :aria-label="__('Remove')" @click="of.unassign(user)" />
        </li>
      </ul>
    </div>

    <div>
      <Head :label="__('Tags')" />
      <div class="flex flex-wrap items-center gap-1.5">
        <Badge v-for="tag in said.tags" :key="tag" :label="tag" theme="gray">
          <template v-if="can.tag" #suffix>
            <button class="lucide-x size-3 text-ink-gray-5 hover:text-ink-gray-8" :aria-label="__('Remove')" @click="of.untag(tag)" />
          </template>
        </Badge>
        <Combobox
          v-if="can.tag"
          v-model:query="query"
          :model-value="null"
          :options="tagOptions"
          :filterable="false"
          trigger="button"
          size="sm"
          variant="ghost"
          :placeholder="__('Add a tag')"
          @update:model-value="addTag"
          @update:open="(open) => open && (query = '')"
        >
          <template #prefix><span class="lucide-plus size-3.5 text-ink-gray-5" /></template>
        </Combobox>
      </div>
    </div>

    <div>
      <Head :label="__('Shared With')" :add="can.share ? of.share : null" />
      <div class="flex items-center gap-2">
        <Badge v-if="said.everyone" :label="__('Everyone')" theme="gray" />
        <button v-if="said.shared.length" class="rounded-3" :aria-label="__('Shared With')" @click="can.share && of.share()">
          <People :users="said.shared" :people="people" :max="5" />
        </button>
      </div>
    </div>

    <Button
      variant="ghost"
      size="sm"
      icon-left="lucide-heart"
      :class="liked && '[&_.lucide-heart]:fill-current [&_.lucide-heart]:text-ink-red-3'"
      :aria-label="liked ? __('Unlike', null, 'Record') : __('Like', null, 'Record')"
      :aria-pressed="liked"
      @click="of.like(!liked)"
    >
      <span v-if="said.liked_by.length" class="tabular-nums">{{ count(said.liked_by.length) }}</span>
    </Button>

    <div class="space-y-2 text-sm text-ink-gray-5">
      <p>{{ said.modified_by === me() ? __("Last Edited By You") : __("Last Edited By {0}", [person(said.modified_by).name]) }}<br />{{ ago(said.modified) }}</p>
      <p>{{ said.owner === me() ? __("Created By You") : __("Created By {0}", [person(said.owner).name]) }}<br />{{ ago(said.creation) }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, ref, watch } from "vue";
import { Avatar, Badge, Button, Combobox } from "frappe-ui";

import { __, ago, count, me, userInfo } from "./desk";
import People from "./People.vue";

const props = defineProps({ of: { type: Object, required: true } });

const said = computed(() => props.of.said.value);
const can = computed(() => props.of.can.value);
const liked = computed(() => said.value?.liked_by.includes(me()));

const person = userInfo;
const people = computed(() => {
  const all = [...(said.value?.assigned || []), ...(said.value?.shared || []), ...props.of.viewers.value];
  return Object.fromEntries(all.map((user) => [user, person(user)]));
});

// The workspace's tags, as frappe's tag box offers them, and a new one from
// what is typed.
const query = ref("");
const found = ref([]);
let asked = 0;
watch(query, async (now) => {
  const mine = ++asked;
  const got = await props.of.tags(now);
  if (mine === asked) found.value = (got || []).filter((tag) => !said.value?.tags.includes(tag));
});
const tagOptions = computed(() => [
  ...found.value,
  {
    type: "custom",
    key: "new",
    label: __("Add {0}", [query.value.trim()]),
    icon: "lucide-plus",
    condition: ({ query: typed }) => !!typed.trim() && !found.value.includes(typed.trim()),
    onClick: ({ query: typed }) => addTag(typed.trim()),
  },
]);
function addTag(tag) {
  if (tag && !said.value.tags.includes(tag)) props.of.tag(tag);
}

// A part's name, with frappe's + beside it where the reader may add.
const Head = defineComponent({
  props: { label: String, add: Function },
  setup(head) {
    return () =>
      h("div", { class: "mb-1.5 flex items-center justify-between" }, [
        h("span", { class: "text-sm font-medium text-ink-gray-5" }, head.label),
        head.add && h(Button, { variant: "ghost", size: "sm", icon: "lucide-plus", "aria-label": head.label, onClick: () => head.add() }),
      ]);
  },
});
</script>
