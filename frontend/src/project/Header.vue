<template>
  <!-- The project's head, as monday's and Asana's: its name, and what is
       changed most, changed right here. -->
  <header class="pt-6">
    <div class="flex flex-wrap items-center gap-3">
      <span class="flex size-9 shrink-0 items-center justify-center rounded-5 bg-surface-gray-2 text-ink-gray-7">
        <span :class="kindIcon" class="size-5" />
      </span>
      <input
        v-if="editing"
        ref="nameInput"
        v-model="name"
        class="min-w-0 flex-1 rounded-3 border-0 bg-surface-gray-2 px-2 py-0.5 text-2xl font-semibold text-ink-gray-9 focus:ring-2 focus:ring-outline-gray-3"
        :aria-label="__('Project Name')"
        @keydown.enter="saveName"
        @keydown.esc="editing = false"
        @blur="saveName"
      />
      <h1 v-else class="min-w-0 truncate text-2xl font-semibold text-ink-gray-9" :class="said.can_write && 'cursor-text rounded-3 hover:bg-surface-gray-2'" @click="startEditing">
        {{ said.title }}
      </h1>
      <Badge :label="__(said.kind)" theme="gray" size="md" />
    </div>

    <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-base text-ink-gray-6">
      <Pill :value="said.status" :options="['Open', 'Completed', 'Cancelled']" :colors="PROJECT_STATUS" :label="__('Status')" :readonly="!said.can_write" @change="(v) => $emit('change', 'status', v)" />
      <Pill :value="said.health" :options="['On Track', 'At Risk', 'Off Track']" :colors="HEALTH" :label="__('Health')" :empty="__('Set Health')" :readonly="!said.can_write" @change="(v) => $emit('change', 'one_health', v)" />
      <button v-if="said.customer" class="flex items-center gap-1.5 hover:text-ink-gray-9" @click="go(`/desk/customer/${said.customer}`)">
        <span class="lucide-building size-4 text-ink-gray-5" />{{ said.customer_name || said.customer }}
      </button>
      <span v-if="dates" class="flex items-center gap-1.5"><span class="lucide-calendar size-4 text-ink-gray-5" />{{ dates }}</span>
      <span v-if="said.manager_name" class="flex items-center gap-1.5">
        <Avatar :label="said.manager_name" size="xs" />{{ said.manager_name }}
      </span>
      <span v-if="progress !== null" class="flex items-center gap-2 whitespace-nowrap">
        <div class="w-24"><Progress :value="progress" size="md" /></div>
        <span class="tabular-nums">{{ __("{0}% done", [progress]) }}</span>
      </span>
      <div class="ms-auto">
        <People :users="said.team.map((one) => one.user)" :people="teamPeople" :max="6" size="md" />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import { Avatar, Badge, Progress } from "frappe-ui";

import { People, Pill, __, date, go } from "../kit";
import { HEALTH, PROJECT_STATUS } from "./colors";

const props = defineProps({
  said: { type: Object, required: true },
  progress: { type: Number, default: null },
});
const emit = defineEmits(["change"]);

const KIND_ICONS = { "Fixed Price": "lucide-file-text", "Time and Materials": "lucide-clock", Retainer: "lucide-repeat", Internal: "lucide-building" };
const kindIcon = computed(() => KIND_ICONS[props.said.kind] || "lucide-folder");
const dates = computed(() => [props.said.starts, props.said.ends].filter(Boolean).map(date).join(" – "));
const teamPeople = computed(() => Object.fromEntries(props.said.team.map((one) => [one.user, one])));

const editing = ref(false);
const name = ref("");
const nameInput = ref(null);
function startEditing() {
  if (!props.said.can_write) return;
  name.value = props.said.title;
  editing.value = true;
  nextTick(() => nameInput.value?.select());
}
function saveName() {
  if (!editing.value) return;
  editing.value = false;
  const now = name.value.trim();
  if (now && now !== props.said.title) emit("change", "project_name", now);
}
</script>
