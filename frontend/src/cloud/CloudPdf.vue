<template>
  <div ref="scroller" class="h-full w-full overflow-auto">
    <div v-if="failed" class="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <span class="lucide-file-x size-12 text-ink-gray-5" aria-hidden="true" />
      <span class="text-base text-ink-gray-7">{{ failed === true ? __("This PDF could not be opened.") : failed }}</span>
    </div>
    <Loading v-else-if="!pages" />
    <div v-else class="flex flex-col items-center gap-3 py-4">
      <div class="sticky top-0 z-10 flex items-center gap-1 rounded-full bg-surface-gray-3 px-1 py-0.5 text-sm text-ink-gray-7">
        <Button size="sm" variant="ghost" icon="lucide-zoom-out" :aria-label="__('Zoom Out')" :title="__('Zoom Out')" :disabled="zoom <= 0.5" @click="zoomBy(-0.25)" />
        <span class="w-12 text-center tabular-nums">{{ Math.round(zoom * 100) }}%</span>
        <Button size="sm" variant="ghost" icon="lucide-zoom-in" :aria-label="__('Zoom In')" :title="__('Zoom In')" :disabled="zoom >= 3" @click="zoomBy(0.25)" />
        <span class="px-2 text-ink-gray-5">{{ pages === 1 ? __("1 page") : __("{0} pages", [pages]) }}</span>
      </div>
      <canvas v-for="number in pages" :key="`${number}-${zoom}`" :ref="(el) => (canvases[number] = el)" :data-page="number" class="border border-outline-gray-2" />
    </div>
  </div>
</template>

<script setup>
// A PDF in the viewer, its pages drawn as they scroll into sight (pdf.js).
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { Loading, __ } from "../kit";
import { drawPage, openPdf } from "./pdf";

const props = defineProps({ node: { type: String, required: true }, src: { type: String, default: null } });

const scroller = ref(null);
const pages = ref(0);
const failed = ref(false);
const zoom = ref(1);
const canvases = {};
let pdf = null;
let seen = null;
const drawn = new Set();

function width() {
  const room = (scroller.value?.clientWidth || 800) - 32;
  return Math.min(room, 900) * zoom.value;
}

function watchPages() {
  seen?.disconnect();
  drawn.clear();
  seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const number = Number(entry.target.dataset.page);
        if (!entry.isIntersecting || drawn.has(number)) continue;
        drawn.add(number);
        drawPage(pdf, number, entry.target, width());
      }
    },
    { root: scroller.value, rootMargin: "600px 0px" }
  );
  Object.values(canvases).forEach((canvas) => canvas && seen.observe(canvas));
}

async function open() {
  failed.value = false;
  pages.value = 0;
  try {
    pdf = await openPdf(props.node, props.src);
    pages.value = pdf.numPages;
    await nextTick();
    watchPages();
  } catch (error) {
    failed.value = props.src && error?.message && !/^\d+$/.test(error.message) ? error.message : true;
  }
}

async function zoomBy(by) {
  zoom.value = Math.min(3, Math.max(0.5, zoom.value + by));
  await nextTick();
  watchPages();
}

watch(() => props.node, open);
onMounted(open);
onBeforeUnmount(() => {
  seen?.disconnect();
  pdf?.destroy();
});
</script>
