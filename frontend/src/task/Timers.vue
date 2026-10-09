<template>
  <!-- The reader's timers. Beside the rail's Timers tile, frappe-ui's Popover
       anchored to the tile (`reference`), opened and closed by the tile
       (desk.js `onedesk.dock.timers_open`). On a phone, which has no rail,
       the page /desk/timers. -->
  <Popover
    v-if="reference"
    trigger="manual"
    :reference="reference"
    :open="open"
    side="right"
    align="end"
    :offset="8"
    @update:open="toggled"
  >
    <div class="w-80 p-3">
      <h3 class="mb-3 text-base font-semibold text-ink-gray-9">{{ __("Timers") }}</h3>
      <TimerList @opened="emit('close')" />
    </div>
  </Popover>
  <div v-else class="mx-auto w-full max-w-2xl px-5 py-6">
    <TimerList />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from "vue";
import { Popover } from "frappe-ui";

import { __ } from "../kit";
import TimerList from "./TimerList.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  // The tile the popover opens beside, and whether it is open.
  reference: { type: Object, default: null },
  open: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);

// A press on the tile is outside the popover, and the tile's own click then
// toggles it. Left to close here too, it would close and open again at once.
let onTile = false;
const pressed = (event) => (onTile = !!props.reference?.contains(event.target));
const clicked = () => setTimeout(() => (onTile = false));

function toggled(value) {
  if (!value && !onTile) emit("close");
}

onMounted(() => {
  document.addEventListener("pointerdown", pressed, true);
  document.addEventListener("click", clicked, true);
});
onUnmounted(() => {
  document.removeEventListener("pointerdown", pressed, true);
  document.removeEventListener("click", clicked, true);
});
</script>
