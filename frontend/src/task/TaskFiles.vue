<template>
  <!-- The task's files: OneCloud on the task's room, as every record's Files
       tab is (record_files.js). -->
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-3">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Files") }}
        <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
      </h2>
    </div>
    <!-- What the workspace's extensions add here (one_studio/places.py). -->
    <PlaceSpot :said="spot" class="mb-4" />
    <div ref="box" class="one-project-files" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

import { PlaceSpot, __, call, jq, onedesk, requires } from "../kit";
import { usePlace } from "../project/place";

const props = defineProps({ task: { type: String, required: true }, subject: String });
const emit = defineEmits(["count"]);
const box = ref(null);

// The page is an island in a shadow root, which desk's styles and icons
// don't reach. The explorer is desk's, so it lives in the page itself and is
// shown here through a slot, styled as on every other record.
let outside = null;
onMounted(async () => {
  await requires(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]);
  if (!box.value) return;
  const slot = document.createElement("slot");
  slot.name = `one-files-${props.task}`;
  box.value.appendChild(slot);
  outside = document.createElement("div");
  outside.slot = slot.name;
  box.value.getRootNode().host.appendChild(outside);
  new (onedesk().OneCloud)(null, { room: `@records/Task/${props.task}`, parent: jq(outside), listed: () => load() });
});
onBeforeUnmount(() => outside?.remove());

const count = ref(0);
const spot = usePlace("onetask_task.files", () => ({ task: { name: props.task, subject: props.subject }, files: { count: count.value } }));
async function load() {
  count.value = await call("onedesk.one_task.view.files", { task: props.task });
  emit("count", count.value);
}
</script>
