<template>
  <!-- The project's name, renamed in place. On a photo it is drawn in white. -->
  <div class="flex min-w-0 flex-wrap items-center gap-3">
    <input
      v-if="editing"
      ref="nameInput"
      v-model="name"
      class="min-w-0 flex-1 rounded-3 border-0 bg-surface-gray-2 px-2 py-0.5 font-semibold text-ink-gray-9 focus:ring-2 focus:ring-outline-gray-3"
      :class="size"
      :aria-label="__('Project Name')"
      @keydown.enter="save"
      @keydown.esc="editing = false"
      @blur="save"
    />
    <h1 v-else class="min-w-0 truncate !font-semibold tracking-tight" :class="[size, onImage ? 'text-white' : 'text-ink-gray-9', said.can_write && (onImage ? 'cursor-text' : 'cursor-text rounded-3 hover:bg-surface-gray-3')]" @click="start">
      {{ said.title }}
    </h1>
  </div>
</template>

<script setup>
import { nextTick, ref } from "vue";

import { __ } from "../kit";

const props = defineProps({ said: { type: Object, required: true }, onImage: Boolean, size: { type: String, default: "text-2xl" } });
const emit = defineEmits(["change"]);


const editing = ref(false);
const name = ref("");
const nameInput = ref(null);
function start() {
  if (!props.said.can_write) return;
  name.value = props.said.title;
  editing.value = true;
  nextTick(() => nameInput.value?.select());
}
function save() {
  if (!editing.value) return;
  editing.value = false;
  const now = name.value.trim();
  if (now && now !== props.said.title) emit("change", "project_name", now);
}
</script>
