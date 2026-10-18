<template>
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-3">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Files") }}
        <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
      </h2>
    </div>
    <PlaceSpot :said="spot" class="mb-4" />
    <div ref="box" class="one-project-files" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { PlaceSpot, __, call, follow, jq, onedesk, requires } from "../kit";
import { onlyArg, useOnly } from "./only";
import { usePlace } from "./place";

const props = defineProps({ project: { type: String, required: true } });
const only = useOnly();
const emit = defineEmits(["count"]);

const room = computed(() => (only.value ? `@own/${props.project}` : `@records/Project/${props.project}`));
const box = ref(null);
let cloud = null;

let outside = null;
onMounted(async () => {
  await requires(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]);
  if (!box.value) return;
  const slot = document.createElement("slot");
  slot.name = `one-files-${props.project}`;
  box.value.appendChild(slot);
  outside = document.createElement("div");
  outside.slot = slot.name;
  box.value.getRootNode().host.appendChild(outside);
  cloud = new (onedesk().OneCloud)(null, { room: room.value, parent: jq(outside), listed: () => load() });
});
watch(room, (now) => cloud?.enter(now));
onBeforeUnmount(() => outside?.remove());

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
