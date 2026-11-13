<template>
  <nav class="flex min-h-0 flex-col overflow-y-auto rounded-6 border border-outline-gray-1 bg-surface-elevation-2 p-2" :aria-label="__('Conversations')" data-tour="onechat-list">
    <section v-for="group in groups" :key="group.kind" class="mb-3">
      <div class="flex items-center justify-between px-2 py-1">
        <h3 class="text-sm font-medium text-ink-gray-5">{{ group.label }}</h3>
        <Dropdown v-if="group.kind === 'Channel'" :options="channelMenu">
          <template #trigger><Button size="sm" variant="ghost" icon="lucide-plus" :aria-label="__('Channels')" :title="__('Channels')" /></template>
        </Dropdown>
        <Button v-else-if="group.kind === 'Direct'" size="sm" variant="ghost" icon="lucide-plus" :aria-label="__('New Message')" :title="__('New Message')" @click="pickPerson" />
      </div>
      <button
        v-for="one in group.rows"
        :key="one.name"
        type="button"
        class="flex w-full items-center gap-2 rounded-3 px-2 py-1.5 text-start text-base"
        :class="one.name === open ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
        @click="$emit('open', one.name)"
      >
        <img v-if="one.agent && agentOf(one.agent)?.face" :src="face(agentOf(one.agent))" alt="" class="size-5 shrink-0 rounded-full bg-surface-gray-2" />
        <Avatar v-else-if="one.kind === 'Direct'" :label="one.with?.name || one.title" :image="one.with?.image" size="sm" />
        <span v-else :class="one.private ? 'lucide-lock' : 'lucide-hash'" class="size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="min-w-0 flex-1 truncate" :class="{ 'font-semibold text-ink-gray-9': one.unread }">{{ one.kind === "Direct" ? one.with?.name || one.title : one.title }}</span>
        <Badge v-if="one.unread" :label="String(one.unread)" theme="blue" size="sm" />
      </button>
      <p v-if="!group.rows.length && group.empty" class="px-2 py-1 text-sm text-ink-gray-5">{{ group.empty }}</p>
    </section>
    <section class="mb-3" data-tour="onechat-agents">
      <h3 class="px-2 py-1 text-sm font-medium text-ink-gray-5">{{ __("Agents", null, "AI") }}</h3>
      <button
        v-for="one in agents"
        :key="one.agent"
        type="button"
        class="flex w-full items-center gap-2 rounded-3 px-2 py-1.5 text-start text-base text-ink-gray-7 hover:bg-surface-gray-2"
        @click="$emit('talk', one.agent)"
      >
        <img v-if="one.face" :src="face(one)" alt="" class="size-5 shrink-0 rounded-full bg-surface-gray-2" />
        <span v-else class="lucide-bot size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="min-w-0 flex-1 truncate">{{ one.name }}</span>
      </button>
    </section>
    <Dialog v-model:open="making" :title="__('New Channel')" size="md">
      <div class="flex flex-col gap-4">
        <FormControl v-model="fresh.title" :label="__('Title')" type="text" required />
        <FormControl v-model="fresh.about" :label="__('Description')" type="textarea" />
        <FormControl v-model="fresh.private" :label="__('Private')" type="checkbox" :description="__('If enabled, only its members can find it.')" />
      </div>
      <template #actions>
        <Button variant="solid" class="w-full" :label="__('Create Channel')" :disabled="!fresh.title.trim()" @click="make" />
      </template>
    </Dialog>
    <Dialog v-model:open="browsing" :title="__('Browse Channels')" size="md">
      <p v-if="!found.length" class="text-base text-ink-gray-5">{{ __("No channels yet") }}</p>
      <div v-for="one in found" :key="one.name" class="flex items-center gap-3 py-2">
        <span class="lucide-hash size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-base text-ink-gray-8">{{ one.title }}</span>
          <span class="truncate text-sm text-ink-gray-5">{{ one.about || __("{0} members", [one.members]) }}</span>
        </span>
        <Button v-if="one.member" size="sm" :label="__('Open')" @click="(browsing = false), $emit('open', one.name)" />
        <Button v-else size="sm" variant="subtle" :label="__('Join')" @click="join(one)" />
      </div>
    </Dialog>
  </nav>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { Avatar, Badge, Button, Dialog, Dropdown, FormControl } from "frappe-ui";

import { __, call, get, me, mentionable, prompt } from "../kit";
import { face, method } from "./chat";

const props = defineProps({
  channels: { type: Array, default: () => [] },
  agents: { type: Array, default: () => [] },
  open: { type: String, default: null },
  mayMake: Boolean,
});
const emit = defineEmits(["open", "talk", "direct", "made"]);

const groups = computed(() => [
  { kind: "Channel", label: __("Channels"), rows: props.channels.filter((one) => one.kind === "Channel"), empty: __("No channels yet") },
  { kind: "Direct", label: __("Direct Messages"), rows: props.channels.filter((one) => one.kind === "Direct") },
  { kind: "Agent", label: __("With Agents"), rows: props.channels.filter((one) => one.kind === "Agent") },
]);

const agentOf = (agent) => props.agents.find((one) => one.agent === agent);

const making = ref(false);
const fresh = reactive({ title: "", about: "", private: false });
const browsing = ref(false);
const found = ref([]);

const channelMenu = computed(() => [
  ...(props.mayMake ? [{ label: __("New Channel"), icon: "plus", onClick: () => (making.value = true) }] : []),
  { label: __("Browse Channels"), icon: "search", onClick: browse },
]);

async function make() {
  const made = await call(method("make"), { title: fresh.title, about: fresh.about, private: fresh.private ? 1 : 0 });
  making.value = false;
  Object.assign(fresh, { title: "", about: "", private: false });
  emit("made", made.name);
}

async function browse() {
  found.value = await get(method("browse"));
  browsing.value = true;
}

async function join(one) {
  await call(method("join"), { channel: one.name });
  browsing.value = false;
  emit("made", one.name);
}

function pickPerson() {
  const people = mentionable().filter((one) => one.value !== me());
  prompt(
    { fieldname: "user", fieldtype: "Autocomplete", label: __("To"), options: people, reqd: 1 },
    ({ user }) => emit("direct", user),
    __("New Message"),
    __("Open"),
  );
}
</script>
