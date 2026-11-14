<template>
  <article class="group flex gap-2.5 rounded-3 px-1 py-1.5 hover:bg-surface-gray-1" :class="{ 'border-b border-outline-gray-1 pb-3': first }">
    <img v-if="agent && agent.face" :src="face(agent)" alt="" class="mt-0.5 size-8 shrink-0 rounded-full bg-surface-gray-2" />
    <Avatar v-else :label="who" :image="person.image" size="lg" class="mt-0.5 shrink-0" />
    <div class="min-w-0 flex-1">
      <div class="flex items-baseline gap-2">
        <span class="text-base font-semibold text-ink-gray-9">{{ who }}</span>
        <Badge v-if="message.agent" :label="__('Agent')" theme="gray" size="sm" />
        <Badge v-else-if="message.automation" :label="message.automation" theme="gray" size="sm" />
        <time class="text-sm text-ink-gray-5" :datetime="message.creation" :title="message.creation">{{ ago(message.creation) }}</time>
        <div class="ms-auto flex gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100">
          <Dropdown :options="reactions">
            <template #trigger><Button size="sm" variant="ghost" icon="lucide-smile-plus" :aria-label="__('Add Reaction')" :title="__('Add Reaction')" /></template>
          </Dropdown>
          <Button v-if="threads" size="sm" variant="ghost" icon="lucide-message-square" :aria-label="__('Reply in Thread')" :title="__('Reply in Thread')" @click="$emit('thread')" />
        </div>
      </div>
      <div v-if="message.text" dir="auto" class="prose prose-sm max-w-none text-start text-base text-ink-gray-8" v-html="said(message.text)" />
      <p v-for="(look, at) in looked" :key="at" class="text-sm text-ink-gray-5">{{ look }}</p>
      <Button v-if="suggested" class="mt-1" size="sm" :label="__('Review Suggestions')" @click="$emit('suggestions')" />
      <div v-if="message.files.length" class="mt-1 flex flex-wrap gap-2">
        <a
          v-for="file in message.files"
          :key="file.name"
          :href="file.file_url"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-1.5 rounded-3 border border-outline-gray-1 px-2 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
        >
          <span class="lucide-file size-4" aria-hidden="true" />
          <span class="max-w-48 truncate">{{ file.file_name }}</span>
        </a>
      </div>
      <AgentCard v-if="card" :card="card" class="mt-2" @changed="(one) => $emit('card', one)" />
      <div v-if="Object.keys(message.reactions || {}).length" class="mt-1 flex flex-wrap gap-1">
        <button
          v-for="(users, emoji) in message.reactions"
          :key="emoji"
          type="button"
          class="flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm"
          :class="users.includes(me()) ? 'border-outline-gray-3 bg-surface-gray-3' : 'border-outline-gray-1'"
          :title="users.map((one) => userInfo(one).name).join(', ')"
          @click="$emit('react', emoji)"
        >
          <span>{{ emoji }}</span>
          <span class="text-ink-gray-7">{{ users.length }}</span>
        </button>
      </div>
      <button v-if="threads && message.replies" type="button" class="mt-1 text-sm font-medium text-ink-blue-3 hover:underline" @click="$emit('thread')">
        {{ message.replies === 1 ? __("1 reply") : __("{0} replies", [message.replies]) }}
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";

import { __, ago, me, userInfo } from "../kit";
import AgentCard from "./AgentCard.vue";
import { REACTIONS, face, said } from "./chat";

const props = defineProps({
  message: { type: Object, required: true },
  agents: { type: Array, default: () => [] },
  card: { type: Object, default: null },
  first: Boolean,
  threads: Boolean,
});
const emit = defineEmits(["thread", "react", "card", "suggestions"]);

const agent = computed(() => props.agents.find((one) => one.agent === props.message.agent) || null);
const person = computed(() => userInfo(props.message.sender));
const who = computed(() => (agent.value ? agent.value.name : person.value.name));

const reactions = REACTIONS.map((emoji) => ({ label: emoji, onClick: () => emit("react", emoji) }));

const looked = computed(() =>
  ((props.message.parts || {}).looked || []).map((look) => {
    const what = (look.args && (look.args.doctype || look.args.name)) || "";
    return what ? __("Looked at {0}", [what]) : __("Looked something up");
  }),
);
const suggested = computed(() => ((props.message.parts || {}).cards || []).length > 0);
</script>
