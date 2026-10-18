<template>
  <div>
    <div v-for="(one, i) in shown" :key="i" class="flex gap-3 pb-4">
      <Avatar :label="one.by" :image="one.image" size="md" />
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 text-base">
          <span class="font-medium text-ink-gray-8">{{ one.by }}</span>
          <span class="text-sm text-ink-gray-5">{{ date(one.on) }}</span>
          <Pill v-if="one.health" :value="one.health" :colors="HEALTH" :label="__('Health')" readonly />
        </div>
        <p class="mt-1 whitespace-pre-line text-base leading-relaxed text-ink-gray-7" :class="!open[i] && 'line-clamp-4'">{{ one.said }}</p>
        <Button v-if="long(one) && !open[i]" variant="ghost" size="sm" class="-ms-2 mt-1" :label="__('Show More')" @click="open[i] = true" />
      </div>
    </div>
    <div v-if="said.update_due && !note" class="mb-2 flex items-center gap-2 text-base text-ink-gray-7">
      <span class="h-2 w-2 rounded-full bg-surface-blue-5" />
      {{ __("Your update is due today") }}
    </div>
    <div ref="line" class="flex items-center gap-2">
      <Pill v-if="said.health && !['Completed', 'Cancelled'].includes(said.status)" :value="said.health" :colors="HEALTH" :label="__('Health')" readonly />
      <TextInput v-model="note" class="min-w-0 flex-1" :placeholder="__('Write an update')" @keydown.enter="post" />
      <Button v-if="note.trim()" variant="solid" :label="__('Post Update')" :loading="posting" @click="post" />
    </div>
    <Button v-if="updates.length > 1" variant="ghost" class="mt-2 -ms-2" :label="all ? __('Show Less') : __('Show {0} Earlier', [updates.length - 1])" @click="all = !all" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Avatar, Button, TextInput } from "frappe-ui";

import { Pill, __, call, date, followList, listen } from "../kit";
import { HEALTH } from "./colors";

const props = defineProps({ said: { type: Object, required: true }, writing: Boolean });
const emit = defineEmits(["changed"]);

const updates = ref([]);
const all = ref(false);
const open = reactive({});
const load = async () => (updates.value = await call("onedesk.one_project.view.updates", { project: props.said.name }));
watch(() => [props.said.name, props.said.modified], load, { immediate: true });
const shown = computed(() => (all.value ? updates.value : updates.value.slice(0, 1)));
const long = (one) => one.said.length > 320 || one.said.split("\n").length > 4;

const note = ref("");
const posting = ref(false);
async function post() {
  if (!note.value.trim() || posting.value) return;
  posting.value = true;
  try {
    await call("onedesk.one_project.updates.post", { project: props.said.name, note: note.value.trim() });
    note.value = "";
    await load();
    emit("changed");
  } finally {
    posting.value = false;
  }
}

const stop = [
  listen("one_project_update", (data) => {
    if (data.project !== props.said.name) return;
    load();
    if (props.said.update_due) emit("changed");
  }),
  listen("one_project_draft", (data) => {
    if (data.project !== props.said.name) return;
    note.value = data.text || "";
    focus();
  }),
  followList("User", load),
];
onBeforeUnmount(() => stop.forEach((one) => one()));

const line = ref(null);
function focus() {
  const input = line.value?.querySelector("input");
  input?.scrollIntoView({ block: "center", behavior: "smooth" });
  input?.focus();
}
watch(() => props.writing, (now) => now && nextTick(() => setTimeout(focus, 300)), { immediate: true });
</script>
