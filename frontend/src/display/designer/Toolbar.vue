<template>
  <div class="flex items-center gap-1 overflow-x-auto border-b border-outline-gray-1 px-3 py-1.5">
    <Button size="sm" variant="ghost" icon="lucide-undo-2" :tooltip="`${__('Undo')} (Ctrl+Z)`" :aria-label="__('Undo')" :disabled="!d.s.past.length" @click="d.undo()" />
    <Button size="sm" variant="ghost" icon="lucide-redo-2" :tooltip="`${__('Redo')} (Ctrl+Shift+Z)`" :aria-label="__('Redo')" :disabled="!d.s.future.length" @click="d.redo()" />
    <span class="mx-1 h-5 w-px shrink-0 bg-surface-gray-3" aria-hidden="true" />

    <template v-if="canDraw">
      <Button size="sm" variant="ghost" icon-left="lucide-type" :label="__('Text')" :tooltip="__('Add Text')" @click="addText" />
      <Button size="sm" variant="ghost" icon-left="lucide-image" :label="__('Picture')" :tooltip="__('Add a Picture')" @click="d.add('image')" />
      <Dropdown :options="shapes">
        <template #default="{ open }">
          <Button size="sm" :variant="open ? 'subtle' : 'ghost'" icon-left="lucide-shapes" icon-right="lucide-chevron-down" :label="__('Shape')" :tooltip="__('Add a Shape')" />
        </template>
      </Dropdown>
      <Button size="sm" variant="ghost" icon-left="lucide-qr-code" :label="__('QR Code')" :tooltip="__('Add a QR Code')" @click="d.add('qr')" />
      <span class="mx-1 h-5 w-px shrink-0 bg-surface-gray-3" aria-hidden="true" />

      <Button size="sm" variant="ghost" icon="lucide-copy-plus" :tooltip="`${__('Duplicate')} (Ctrl+D)`" :aria-label="__('Duplicate')" :disabled="!chosen" @click="d.duplicate()" />
      <Dropdown :options="stack">
        <template #default="{ open }">
          <Button size="sm" :variant="open ? 'subtle' : 'ghost'" icon="lucide-layers" :tooltip="__('Arrange')" :aria-label="__('Arrange')" :disabled="!chosen" />
        </template>
      </Dropdown>
      <Button size="sm" variant="ghost" icon="lucide-trash-2" :tooltip="`${__('Delete')} (Del)`" :aria-label="__('Delete')" :disabled="!chosen" @click="d.remove()" />
    </template>

    <span class="min-w-2 flex-1" />
    <Dropdown v-if="d.design.value" :options="zooms" align="end">
      <template #default="{ open }">
        <Button size="sm" :variant="open ? 'subtle' : 'ghost'" icon-right="lucide-chevron-down" :label="zoomLabel" :tooltip="__('Zoom')" />
      </template>
    </Dropdown>
    <Button size="sm" variant="solid" :label="__('Save')" :tooltip="`${__('Save')} (Ctrl+S)`" :loading="saving" :disabled="!d.s.dirty || !d.writable.value" @click="emit('save')" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Button, Dropdown } from "frappe-ui";

import { __ } from "../../kit";
import { glyph } from "./icons";
import { useDesigner } from "./store";

defineProps({ saving: { type: Boolean, default: false } });
const emit = defineEmits(["save"]);
const d = useDesigner();

const canDraw = computed(() => Boolean(d.design.value) && d.writable.value);
const chosen = computed(() => d.chosenBlocks.value.length > 0);

const shapes = computed(() => {
  const spec = d.s.schema?.properties.shape;
  if (!spec) return [];
  return spec.options.map((shape, i) => ({
    label: spec.labels[i],
    icon: glyph(spec.icons[i]),
    onClick: () => d.add("shape", shape === "line" ? { shape, h: 1, radius: 0, opacity: 1 } : { shape }),
  }));
});

const stack = computed(() => [
  { label: __("Bring to Front"), icon: "lucide-bring-to-front", onClick: () => d.restack("front") },
  { label: __("Bring Forward"), icon: "lucide-arrow-up", onClick: () => d.restack("forward") },
  { label: __("Send Back"), icon: "lucide-arrow-down", onClick: () => d.restack("backward") },
  { label: __("Send to Back"), icon: "lucide-send-to-back", onClick: () => d.restack("back") },
]);

const zooms = computed(() => [
  { label: __("Fit"), onClick: () => (d.s.zoom = "fit") },
  ...[0.25, 0.5, 0.75, 1].map((z) => ({ label: `${z * 100}%`, onClick: () => (d.s.zoom = z) })),
]);
const zoomLabel = computed(() => (d.s.zoom === "fit" ? __("Fit") : `${d.s.zoom * 100}%`));

const addText = () => d.add("text", { text: __("Your words here") });
</script>
