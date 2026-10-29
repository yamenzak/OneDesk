<template>
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-3">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Files") }}
        <span v-if="count" class="text-base font-normal text-ink-gray-5">{{ count }}</span>
      </h2>
    </div>
    <PlaceSpot :said="spot" class="mb-4" />
    <div class="h-[36rem] overflow-hidden rounded-4 border border-outline-gray-1"><OneCloud :room="`@records/Item/${item}`" :on-listed="load" /></div>
  </div>
</template>

<script setup>
import { ref } from "vue";

import { PlaceSpot, __, call } from "../../kit";
import OneCloud from "../../cloud/OneCloud.vue";
import { usePlace } from "../../project/place";

const props = defineProps({ item: { type: String, required: true }, title: String });
const emit = defineEmits(["count"]);

const count = ref(0);
const spot = usePlace("oneinventory_item.files", () => ({ item: { name: props.item, item_name: props.title }, files: { count: count.value } }));
async function load() {
  count.value = await call("onedesk.one_inventory.view.files", { item: props.item });
  emit("count", count.value);
}
</script>
