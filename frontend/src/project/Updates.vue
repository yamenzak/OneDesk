<template>
  <!-- The team's latest update, and a line to post the next one with the
       project's health. Earlier ones open under it. -->
  <div>
    <div v-for="(one, i) in shown" :key="i" class="flex gap-3 pb-4">
      <Avatar :label="one.by" size="md" />
      <div class="min-w-0 flex-1">
        <div class="flex items-baseline gap-2 text-base">
          <span class="font-medium text-ink-gray-8">{{ one.by }}</span>
          <span class="text-sm text-ink-gray-5">{{ date(one.on) }}</span>
        </div>
        <p class="mt-1 text-base leading-relaxed text-ink-gray-7">{{ one.said }}</p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <Pill :value="health" :options="HEALTHS" :colors="HEALTH" :label="__('Health')" @change="(v) => (health = v)" />
      <TextInput v-model="note" class="min-w-0 flex-1" :placeholder="__('Write an update')" @keydown.enter="post" />
      <Button v-if="note.trim()" variant="solid" :label="__('Post')" :loading="posting" @click="post" />
    </div>
    <Button v-if="updates.length > 1" variant="ghost" class="mt-2 -ms-2" :label="all ? __('Show Less') : __('Show {0} Earlier', [updates.length - 1])" @click="all = !all" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Button, TextInput } from "frappe-ui";

import { Pill, __, call, date, setValue } from "../kit";
import { HEALTH } from "./colors";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const HEALTHS = ["On Track", "At Risk", "Off Track"];

const updates = ref([]);
const all = ref(false);
const load = async () => (updates.value = await call("onedesk.one_project.view.updates", { project: props.said.name }));
watch(() => [props.said.name, props.said.modified], load, { immediate: true });
const shown = computed(() => (all.value ? updates.value : updates.value.slice(0, 1)));

const health = ref(props.said.health || "On Track");
watch(() => props.said.health, (now) => now && (health.value = now));
const note = ref("");
const posting = ref(false);
async function post() {
  if (!note.value.trim() || posting.value) return;
  posting.value = true;
  try {
    if (health.value !== props.said.health) await setValue("Project", props.said.name, "one_health", health.value);
    await call("onedesk.one_project.updates.post", { project: props.said.name, note: note.value.trim() });
    note.value = "";
    await load();
    emit("changed");
  } finally {
    posting.value = false;
  }
}
</script>
