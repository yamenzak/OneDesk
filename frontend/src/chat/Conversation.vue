<template>
  <section class="flex h-full min-h-0 flex-col overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-elevation-2" data-tour="onechat-conversation">
    <header class="flex items-center gap-2 border-b border-outline-gray-1 px-3 py-2">
      <Button v-if="back" size="sm" variant="ghost" icon="lucide-arrow-left" :aria-label="__('Back')" @click="$emit('back')" />
      <img v-if="agentOf(info.agent)?.face" :src="face(agentOf(info.agent))" alt="" class="size-6 rounded-full bg-surface-gray-2" />
      <span v-else-if="!thread && info.kind === 'Channel'" :class="info.private ? 'lucide-lock' : 'lucide-hash'" class="size-4 text-ink-gray-5" aria-hidden="true" />
      <div class="flex min-w-0 flex-1 flex-col">
        <h2 class="truncate text-base font-semibold text-ink-gray-9">{{ thread ? __("Thread") : info.title }}</h2>
        <span v-if="!thread && info.about" class="truncate text-sm text-ink-gray-5">{{ info.about }}</span>
      </div>
      <People v-if="!thread && info.kind === 'Channel'" :users="people" :people="peopleInfo" size="sm" />
      <Dropdown v-if="!thread && info.kind === 'Channel'" :options="menu">
        <template #trigger><Button size="sm" variant="ghost" icon="lucide-more-horizontal" :aria-label="__('More')" /></template>
      </Dropdown>
      <Button v-if="thread" size="sm" variant="ghost" icon="lucide-x" :aria-label="__('Close')" @click="$emit('close')" />
    </header>
    <div ref="body" class="min-h-0 flex-1 overflow-y-auto px-3 py-2">
      <Loading v-if="loading" />
      <template v-else>
        <div v-if="more" class="flex justify-center py-2">
          <Button size="sm" variant="ghost" :label="__('Show Earlier')" @click="earlier" />
        </div>
        <p v-if="!messages.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No messages yet") }}</p>
        <Message
          v-for="(one, at) in messages"
          :key="one.name"
          :message="one"
          :agents="agents"
          :card="one.action ? cards[one.action] : null"
          :first="thread && at === 0"
          :threads="!thread && info.kind === 'Channel'"
          @thread="$emit('thread', one.name)"
          @react="(emoji) => react(one, emoji)"
          @card="(card) => (cards = { ...cards, [card.name]: card })"
          @suggestions="review"
        />
        <div v-if="answering" class="flex items-center gap-2 py-2 text-sm text-ink-gray-5" aria-live="polite">
          <LoadingIndicator class="size-3" />
          <span>{{ __("{0} is answering…", [answering]) }}</span>
        </div>
        <OneAlert v-if="failed" colour="red" :text="failed" />
      </template>
    </div>
    <Composer
      :channel="channel"
      :thread="thread"
      :members="people"
      :agents="agents"
      :placeholder="placeholder"
      :busy="!!answering"
      @sent="sent"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { Button, Dropdown, LoadingIndicator } from "frappe-ui";

import { Loading, OneAlert, People, __, call, get, listen, listenTo, mentionable, onedesk, prompt, userInfo } from "../kit";
import { face, method } from "./chat";
import Composer from "./Composer.vue";
import Message from "./Message.vue";

const props = defineProps({
  channel: { type: String, required: true },
  thread: { type: String, default: null },
  agents: { type: Array, default: () => [] },
  back: Boolean,
});
const emit = defineEmits(["back", "thread", "close", "left"]);

const info = ref({});
const messages = ref([]);
const cards = ref({});
const more = ref(false);
const loading = ref(true);
const answering = ref("");
const failed = ref("");
const body = ref(null);
let running = null;

const agentOf = (agent) => props.agents.find((one) => one.agent === agent);
const people = computed(() => (info.value.members || []).filter((one) => one.user && !one.agent).map((one) => one.user));
const peopleInfo = computed(() => Object.fromEntries(people.value.map((user) => [user, userInfo(user)])));
const placeholder = computed(() => {
  if (props.thread) return __("Reply");
  if (info.value.kind === "Agent") return __("Ask {0}", [agentOf(info.value.agent)?.name || info.value.title || ""]);
  return __("Message {0}", [info.value.title || ""]);
});

const menu = computed(() => [
  { label: __("Add People"), icon: "user-plus", onClick: addPeople },
  { label: __("Leave Channel"), icon: "log-out", onClick: leave },
]);

async function load(before) {
  const got = await get(method("channel"), { channel: props.channel, thread: props.thread, before });
  info.value = got;
  cards.value = { ...cards.value, ...got.cards };
  messages.value = before ? [...got.messages, ...messages.value] : got.messages;
  more.value = got.more;
  loading.value = false;
  if (!before) toBottom();
  if (!before && !props.thread) call(method("seen"), { channel: props.channel });
}

const earlier = () => load(messages.value[props.thread ? 1 : 0]?.creation);

function toBottom() {
  nextTick(() => body.value && (body.value.scrollTop = body.value.scrollHeight));
}

function heard(said) {
  if (said.channel !== props.channel) return;
  const mine = props.thread ? said.thread === props.thread : !said.thread;
  if (mine && !messages.value.some((one) => one.name === said.name)) {
    messages.value = [...messages.value, said];
    if (said.agent) answering.value = "";
    if (said.action) refreshCard(said.action);
    toBottom();
  }
  if (!props.thread && said.thread) {
    messages.value = messages.value.map((one) => (one.name === said.thread ? { ...one, replies: (one.replies || 0) + 1, last_reply_on: said.creation } : one));
  }
}

function changed(said) {
  if (said.channel !== props.channel) return;
  messages.value = messages.value.map((one) => (one.name === said.name ? said : one));
  if (said.action) refreshCard(said.action);
}

async function refreshCard(action) {
  const found = await get("onedesk.one_chat.panel.actions", { names: [action] });
  if (found && found[0]) cards.value = { ...cards.value, [action]: found[0] };
}

// An agent's answer runs in the background (one_ai/chat.py); its steps are
// told to the asker, and the answer arrives as a message.
function followed(step) {
  if (!running || step.run !== running) return;
  if (step.failed) {
    failed.value = step.failed;
    answering.value = "";
    running = null;
  } else if (step.done) {
    answering.value = "";
    running = null;
  }
}

function sent(got) {
  failed.value = "";
  heard(got.message);
  if (got.run) {
    running = got.run;
    answering.value = agentOf(got.agent)?.name || "";
  }
}

async function react(one, emoji) {
  const reactions = await call(method("react"), { message: one.name, emoji });
  messages.value = messages.value.map((m) => (m.name === one.name ? { ...m, reactions } : m));
}

function review() {
  onedesk()?.oneai?.open({ chat: props.channel });
}

function addPeople() {
  const inside = new Set(people.value);
  prompt(
    { fieldname: "people", fieldtype: "MultiSelectPills", label: __("People"), reqd: 1, get_data: (txt) => mentionable().filter((one) => !inside.has(one.value) && one.label.toLowerCase().includes((txt || "").toLowerCase())) },
    async ({ people: chosen }) => {
      await call(method("add"), { channel: props.channel, people: chosen });
      load();
    },
    __("Add People"),
    __("Add"),
  );
}

async function leave() {
  await call(method("leave"), { channel: props.channel });
  emit("left");
}

const stop = [listenTo("Chat Channel", props.channel, { one_chat_message: heard, one_chat_changed: changed }), listen("one_ai_run", followed)];
onBeforeUnmount(() => stop.forEach((one) => one()));

load();
</script>
