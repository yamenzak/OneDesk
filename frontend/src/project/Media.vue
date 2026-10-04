<template>
  <!-- The project's featured photos and videos, one at a time, with the rest
       under it: frappe-ui's Dialog. -->
  <Dialog v-model:open="open" :title="item?.title" size="4xl">
    <div v-if="item" class="flex flex-col gap-4">
      <div class="relative flex h-[60vh] items-center justify-center overflow-hidden rounded-5 bg-surface-gray-2">
        <video v-if="item.kind === 'video'" :key="item.url" :src="item.url" controls class="max-h-full max-w-full" />
        <img v-else :src="item.url" :alt="item.title" class="max-h-full max-w-full object-contain" />
        <template v-if="media.length > 1">
          <Button class="absolute start-3 top-1/2 -translate-y-1/2" icon="lucide-chevron-left" :aria-label="__('Previous')" @click="move(-1)" />
          <Button class="absolute end-3 top-1/2 -translate-y-1/2" icon="lucide-chevron-right" :aria-label="__('Next')" @click="move(1)" />
        </template>
      </div>
      <div v-if="media.length > 1" class="flex gap-2 overflow-x-auto">
        <button v-for="(one, i) in media" :key="one.name" class="size-16 shrink-0 overflow-hidden rounded-4 ring-2" :class="i === at ? 'ring-outline-gray-5' : 'ring-transparent'" :aria-label="one.title" @click="at = i">
          <Thumb :item="one" />
        </button>
      </div>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button v-if="canAdd" icon-left="lucide-image-plus" :label="__('Add Photos')" @click="$emit('add')" />
        <Button icon-left="lucide-folder-open" :label="__('Open Folder')" @click="openFolder" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, watch } from "vue";
import { Button, Dialog } from "frappe-ui";

import { __, go } from "../kit";
import Thumb from "./Thumb.vue";

const props = defineProps({ media: { type: Array, required: true }, project: { type: String, required: true }, canAdd: Boolean });
defineEmits(["add"]);
const open = defineModel("open", { type: Boolean, default: false });
const at = defineModel("at", { type: Number, default: 0 });
const item = computed(() => props.media[at.value] || props.media[0]);
watch(() => props.media.length, (n) => at.value >= n && (at.value = 0));

const move = (by) => (at.value = (at.value + by + props.media.length) % props.media.length);
function openFolder() {
  open.value = false;
  go(["onecloud", { node: `@featured/${props.project}` }]);
}
</script>
