<template>
  <!-- The item's files: OneCloud on the item's room, as every record's Files
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

const props = defineProps({ item: { type: String, required: true }, title: String });
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
  slot.name = `one-files-${props.item}`;
  box.value.appendChild(slot);
  outside = document.createElement("div");
  outside.slot = slot.name;
  box.value.getRootNode().host.appendChild(outside);
  new (onedesk().OneCloud)(null, { room: `@records/Item/${props.item}`, parent: jq(outside), listed: () => load() });
});
onBeforeUnmount(() => outside?.remove());

const count = ref(0);
const spot = usePlace("oneinventory_item.files", () => ({ item: { name: props.item, item_name: props.title }, files: { count: count.value } }));
async function load() {
  count.value = await call("onedesk.one_inventory.view.files", { item: props.item });
  emit("count", count.value);
}
</script>
