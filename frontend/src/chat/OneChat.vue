<template>
  <div class="flex h-full min-h-0 gap-2.5 px-2.5 pb-2 text-ink-gray-8" data-tour="onechat">
    <ChannelList
      class="shrink-0"
      :class="stacked ? (open ? 'hidden' : 'w-full') : 'w-64'"
      :channels="channels"
      :agents="agents"
      :open="open"
      :may-make="mayMake"
      @open="choose"
      @talk="talk"
      @direct="direct"
      @made="made"
    />
    <div class="min-w-0 flex-1" :class="{ hidden: stacked && (!open || thread) }">
      <div v-if="!open" class="flex h-full flex-col items-center justify-center gap-2 text-ink-gray-5">
        <span class="lucide-message-circle size-6" aria-hidden="true" />
        <span class="text-base">{{ channels.length ? __("No conversation open") : __("No conversations yet") }}</span>
      </div>
      <Conversation
        v-else
        :key="open"
        :channel="open"
        :agents="agents"
        :back="stacked"
        @back="choose(null)"
        @thread="(name) => (thread = name)"
        @left="left"
      />
    </div>
    <Conversation
      v-if="open && thread"
      :key="`${open}:${thread}`"
      :class="stacked ? 'w-full' : 'w-96 shrink-0'"
      :channel="open"
      :thread="thread"
      :agents="agents"
      @close="thread = null"
    />
  </div>
</template>

<script setup>
// OneChat (one_chat/api.py): the reader's conversations down the side, the
// one open beside them, and a thread beside that, as Slack and Gameplan
// draw them. Each list of conversations is live (one_chat/messages.py).
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { __, call, get, listen, name, onResize, setQuery, viewWidth } from "../kit";
import { method } from "./chat";
import ChannelList from "./ChannelList.vue";
import Conversation from "./Conversation.vue";

const props = defineProps({
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
});

props.onTitle?.({ title: name("one_chat") });

const channels = ref([]);
const agents = ref([]);
const mayMake = ref(false);
const open = ref(props.query.channel || null);
const thread = ref(props.query.thread || null);
const wide = ref(viewWidth());
const stacked = computed(() => wide.value < 768);

async function load() {
  const started = await get(method("start"));
  agents.value = started.agents || [];
  channels.value = started.channels || [];
  mayMake.value = Boolean(started.may_make);
}

async function refresh() {
  channels.value = await get(method("conversations"));
}

function choose(name) {
  open.value = name;
  thread.value = null;
  setQuery("channel", name, { push: true });
  setQuery("thread", null);
  if (name) channels.value = channels.value.map((one) => (one.name === name ? { ...one, unread: 0 } : one));
}

watch(thread, (now) => setQuery("thread", now));

async function talk(agent) {
  const made = await call(method("talk"), { agent });
  await refresh();
  choose(made.name);
}

async function direct(user) {
  const made = await call(method("direct"), { user });
  await refresh();
  choose(made.name);
}

async function made(name) {
  await refresh();
  choose(name);
}

async function left() {
  choose(null);
  await refresh();
}

const stop = [
  listen("one_chat_unread", (said) => {
    if (said.channel === open.value && !said.thread) return;
    refresh();
  }),
  onResize(() => (wide.value = viewWidth())),
];
onBeforeUnmount(() => stop.forEach((one) => one && one()));

load();
</script>
