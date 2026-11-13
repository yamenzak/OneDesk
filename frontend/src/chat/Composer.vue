<template>
  <footer class="relative border-t border-outline-gray-1 p-2" data-tour="onechat-composer">
    <ul v-if="offered.length" class="absolute bottom-full start-2 mb-1 w-64 rounded-4 border border-outline-gray-2 bg-surface-elevation-3 p-1" role="listbox" :aria-label="__('Mention')">
      <li v-for="(one, at) in offered" :key="one.key">
        <button
          type="button"
          class="flex w-full items-center gap-2 rounded-3 px-2 py-1.5 text-start text-base"
          :class="at === picked ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-2'"
          @mousedown.prevent="mention(one)"
        >
          <img v-if="one.face" :src="one.face" alt="" class="size-5 rounded-full bg-surface-gray-2" />
          <Avatar v-else :label="one.label" :image="one.image" size="sm" />
          <span class="truncate">{{ one.label }}</span>
        </button>
      </li>
    </ul>
    <div v-if="files.length" class="mb-2 flex flex-wrap gap-2">
      <span v-for="(file, at) in files" :key="file.name" class="flex items-center gap-1 rounded-3 bg-surface-gray-2 px-2 py-1 text-sm">
        <span class="max-w-48 truncate">{{ file.file_name }}</span>
        <Button size="sm" variant="ghost" icon="lucide-x" :aria-label="__('Remove')" @click="files.splice(at, 1)" />
      </span>
    </div>
    <div class="flex items-end gap-2">
      <Button variant="ghost" icon="lucide-paperclip" :aria-label="__('Attach a File')" :title="__('Attach a File')" @click="attach" />
      <textarea
        ref="box"
        v-model="text"
        rows="1"
        dir="auto" class="max-h-40 min-h-9 flex-1 resize-none rounded-2 border border-transparent bg-surface-gray-2 px-2.5 py-1.5 text-base text-ink-gray-8 placeholder-ink-gray-4 hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none focus:ring-0"
        :placeholder="placeholder"
        :aria-label="placeholder"
        @input="fit"
        @keydown="key"
      />
      <Button variant="solid" icon="lucide-send-horizontal" :aria-label="__('Send')" :title="__('Send')" :loading="sending" :disabled="busy || (!text.trim() && !files.length)" @click="send" />
    </div>
  </footer>
</template>

<script setup>
// What a person writes: @ offers the conversation's people and the agents,
// a file comes from OneCloud or the computer (frappe's uploader, attached to
// the conversation, so its members alone open it), Enter sends.
import { computed, nextTick, ref } from "vue";
import { Avatar, Button } from "frappe-ui";

import { __, call, upload, userInfo } from "../kit";
import { face, method } from "./chat";

const props = defineProps({
  channel: { type: String, required: true },
  thread: { type: String, default: null },
  members: { type: Array, default: () => [] },
  agents: { type: Array, default: () => [] },
  placeholder: { type: String, default: "" },
  busy: Boolean,
});
const emit = defineEmits(["sent"]);

const text = ref("");
const files = ref([]);
const box = ref(null);
const sending = ref(false);
const picked = ref(0);

const asking = computed(() => {
  const found = /(?:^|\s)@([^@\n]{0,30})$/.exec(text.value);
  return found ? found[1].toLowerCase() : null;
});

const offered = computed(() => {
  if (asking.value === null) return [];
  const people = props.members.map((user) => ({ key: user, label: userInfo(user).name, image: userInfo(user).image }));
  const agents = props.agents.map((one) => ({ key: one.agent, label: one.handle, face: face(one) }));
  return [...agents, ...people].filter((one) => one.label.toLowerCase().startsWith(asking.value)).slice(0, 8);
});

function mention(one) {
  text.value = text.value.replace(/@([^@\n]{0,30})$/, `@${one.label} `);
  picked.value = 0;
  nextTick(() => box.value && box.value.focus());
}

function key(event) {
  if (offered.value.length && ["ArrowDown", "ArrowUp"].includes(event.key)) {
    event.preventDefault();
    const step = event.key === "ArrowDown" ? 1 : -1;
    picked.value = (picked.value + step + offered.value.length) % offered.value.length;
    return;
  }
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (offered.value.length) return mention(offered.value[picked.value] || offered.value[0]);
    send();
  }
}

function fit() {
  const el = box.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
}

function attach() {
  upload("Chat Channel", props.channel, (file) => files.value.push({ name: file.name, file_name: file.file_name }));
}

async function send() {
  if (sending.value || props.busy || (!text.value.trim() && !files.value.length)) return;
  sending.value = true;
  try {
    const got = await call(method("send"), { channel: props.channel, thread: props.thread, text: text.value, files: files.value.map((one) => one.name) });
    text.value = "";
    files.value = [];
    nextTick(fit);
    emit("sent", got);
  } finally {
    sending.value = false;
  }
}
</script>
