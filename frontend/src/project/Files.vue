<template>
  <!-- The project's files: OneCloud on the project's room, as every record's
       Files tab is (record_files.js). The room holds the project's own files,
       its Featured Media, its tasks' files and a folder per sub-project; on
       the page's Main, the project's own without the sub-projects
       (one_storage/namespace.py `attachments`, `OWN`). -->
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-3">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Files") }}
        <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
      </h2>
    </div>
    <div ref="box" class="one-project-files" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { __, call, follow, jq, onedesk, requires } from "../kit";
import { onlyArg, useOnly } from "./only";

const props = defineProps({ project: { type: String, required: true } });
// Only the project's own work when the page shows its Main (only.js).
const only = useOnly();
const emit = defineEmits(["count"]);

const room = computed(() => (only.value ? `@own/${props.project}` : `@records/Project/${props.project}`));
const box = ref(null);
let cloud = null;

// The page is an island in a shadow root, which desk's styles and icons
// don't reach. The explorer is desk's, so it lives in the page itself and is
// shown here through a slot, styled as on every other record.
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

// How many files the project has, the tab's count: its own, its sub-projects'
// and their tasks'.
const count = ref(0);
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
