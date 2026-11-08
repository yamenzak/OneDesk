<template>
  <div class="flex h-full w-full flex-col">
    <div class="relative min-h-0 flex-1 p-6 max-sm:p-3">
      <img ref="picture" :src="source" alt="" class="block max-w-full" />
      <Loading v-if="!editor && !failed" class="absolute inset-0" />
      <div v-if="failed" class="absolute inset-0 flex items-center justify-center text-base text-ink-gray-7">{{ __("This picture could not be opened.") }}</div>
    </div>
    <div v-if="editor" class="flex shrink-0 flex-col gap-3 border-t border-outline-gray-1 bg-surface-base px-3 py-3">
      <div class="flex flex-wrap items-center gap-2">
        <TabButtons v-model="tool" :options="tools" />
        <span class="flex-1" />
        <Button size="sm" variant="ghost" icon-left="lucide-undo-2" :label="__('Reset')" @click="startOver" />
      </div>
      <div v-if="tool === 'crop'" class="flex flex-wrap items-center gap-x-4 gap-y-3">
        <TabButtons v-model="shape" :options="shapes" />
        <div class="flex items-center gap-1">
          <Button size="sm" variant="ghost" icon="lucide-rotate-ccw" :aria-label="__('Rotate Left')" :title="__('Rotate Left')" @click="turn(editor, -90)" />
          <Button size="sm" variant="ghost" icon="lucide-rotate-cw" :aria-label="__('Rotate Right')" :title="__('Rotate Right')" @click="turn(editor, 90)" />
          <Button size="sm" variant="ghost" icon="lucide-flip-horizontal-2" :aria-label="__('Flip Horizontal')" :title="__('Flip Horizontal')" @click="flip(editor, true)" />
          <Button size="sm" variant="ghost" icon="lucide-flip-vertical-2" :aria-label="__('Flip Vertical')" :title="__('Flip Vertical')" @click="flip(editor, false)" />
        </div>
        <div class="flex min-w-48 flex-1 items-center gap-3">
          <span class="shrink-0 text-sm text-ink-gray-6">{{ __("Straighten") }}</span>
          <Slider v-model="angle" :min="-45" :max="45" :step="1" class="flex-1" />
          <span class="w-10 shrink-0 text-end text-sm tabular-nums text-ink-gray-6">{{ angle[0] }}°</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm text-ink-gray-6">{{ __("Width (px)") }}</span>
          <TextInput v-model="width" type="number" size="sm" class="w-24" :placeholder="String(full)" />
        </div>
      </div>
      <div v-else class="grid gap-x-6 gap-y-3 sm:grid-cols-3">
        <div v-for="one in adjustments" :key="one.key" class="flex items-center gap-3">
          <span class="w-20 shrink-0 text-sm text-ink-gray-6">{{ one.label }}</span>
          <Slider v-model="adjust[one.key]" :min="-100" :max="100" :step="1" class="flex-1" />
          <span class="w-8 shrink-0 text-end text-sm tabular-nums text-ink-gray-6">{{ adjust[one.key][0] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { Button, Slider, TabButtons, TextInput } from "frappe-ui";

import { Loading, __ } from "../kit";
import { contentUrl, extension } from "./cloud";
import { finished, fit, flip, fullWidth, look, reset, startEditor, stopEditor, straighten, turn } from "./editor";

const props = defineProps({ item: { type: Object, required: true } });

const picture = ref(null);
const editor = ref(null);
const failed = ref(false);
const tool = ref("crop");
const shape = ref("free");
const angle = ref([0]);
const width = ref("");
const full = ref(0);
const adjust = reactive({ brightness: [0], contrast: [0], saturation: [0] });

const source = computed(() => contentUrl(props.item.id));

const tools = [
  { label: __("Crop"), value: "crop" },
  { label: __("Adjust"), value: "adjust" },
];
const shapes = [
  { label: __("Free"), value: "free" },
  { label: __("Original"), value: "original" },
  { label: "1:1", value: "1" },
  { label: "4:3", value: String(4 / 3) },
  { label: "16:9", value: String(16 / 9) },
];
const adjustments = [
  { key: "brightness", label: __("Brightness") },
  { key: "contrast", label: __("Contrast") },
  { key: "saturation", label: __("Saturation") },
];

const values = () => ({ brightness: adjust.brightness[0], contrast: adjust.contrast[0], saturation: adjust.saturation[0] });

function ratioOf(value) {
  if (value === "free") return NaN;
  if (value === "original") {
    const shown = picture.value;
    return shown && shown.naturalHeight ? shown.naturalWidth / shown.naturalHeight : NaN;
  }
  return Number(value);
}

const measure = () => editor.value && (full.value = fullWidth(editor.value));

watch(shape, (value) => editor.value && (fit(editor.value, ratioOf(value)), measure()));
watch(angle, ([value]) => editor.value && (straighten(editor.value, value), measure()));
watch(adjust, () => editor.value && look(editor.value, values()));

function startOver() {
  angle.value = [0];
  shape.value = "free";
  width.value = "";
  Object.keys(adjust).forEach((key) => (adjust[key] = [0]));
  reset(editor.value);
  fit(editor.value, NaN);
  measure();
}

onMounted(() => {
  picture.value.addEventListener(
    "load",
    async () => {
      try {
        const made = await startEditor(picture.value);
        made.selection.addEventListener("change", () => requestAnimationFrame(measure));
        editor.value = made;
        measure();
      } catch {
        failed.value = true;
      }
    },
    { once: true }
  );
  picture.value.addEventListener("error", () => (failed.value = true), { once: true });
});
onBeforeUnmount(() => stopEditor(editor.value));

defineExpose({
  make: () => finished(editor.value, { extension: extension(props.item), width: Number(width.value) || 0, adjust: values() }),
  ready: computed(() => Boolean(editor.value)),
});
</script>
