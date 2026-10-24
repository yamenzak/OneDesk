<template>
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-3">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Files") }}
        <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
      </h2>
    </div>
    <PlaceSpot :said="spot" class="mb-4" />
    <div class="h-[36rem] overflow-hidden rounded-4 border border-outline-gray-1"><OneCloud :room="room" :on-listed="load" /></div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

import { PlaceSpot, __, call, follow } from "../kit";
import { onlyArg, useOnly } from "./only";
import OneCloud from "../cloud/OneCloud.vue";
import { usePlace } from "./place";

const props = defineProps({ project: { type: String, required: true } });
const only = useOnly();
const emit = defineEmits(["count"]);

const room = computed(() => (only.value ? `@own/${props.project}` : `@records/Project/${props.project}`));

const count = ref(0);
const spot = usePlace("oneproject.files", () => ({ project: { name: props.project }, files: { count: count.value } }));
async function load() {
  count.value = (await call("onedesk.one_project.view.files", { project: props.project, ...onlyArg(only) })).length;
  emit("count", count.value);
}
let stop = () => {};
watch(
  () => props.project,
  (now) => {
    stop();
    stop = follow("Project", now, load);
    load();
  },
  { immediate: true }
);
watch(only, load);
onBeforeUnmount(() => stop());
</script>
