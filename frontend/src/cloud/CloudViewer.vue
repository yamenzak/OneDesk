<template>
  <Teleport :to="target || 'body'">
  <div
    class="fixed inset-0 z-50 flex flex-col border-outline-gray-2 bg-surface-base text-ink-gray-8 outline-none"
    role="dialog"
    aria-modal="true"
    :aria-label="item?.name || __('File')"
    tabindex="-1"
    ref="root"
    @keydown="key"
    @touchstart.passive="touchStart"
    @touchend.passive="touchEnd"
  >
    <div class="flex shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3 py-2">
      <span :class="[iconOf(item), inkOf(item)]" class="size-5 shrink-0" aria-hidden="true" />
      <span class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-9" :title="item?.name">{{ item?.name }}</span>
      <span v-if="files.length > 1" class="shrink-0 text-sm text-ink-gray-5 max-sm:hidden">{{ __("{0} of {1}", [at + 1, files.length]) }}</span>
      <Button v-if="files.length > 1" variant="ghost" icon="lucide-chevron-left" :aria-label="__('Previous')" :title="__('Previous')" :disabled="at === 0" @click="step(-1)" />
      <Button v-if="files.length > 1" variant="ghost" icon="lucide-chevron-right" :aria-label="__('Next')" :title="__('Next')" :disabled="at === files.length - 1" @click="step(1)" />
      <span class="mx-1 h-5 w-px bg-surface-gray-4" />
      <slot name="actions" :item="item" />
      <Button variant="ghost" icon="lucide-download" :aria-label="__('Download')" :title="__('Download')" @click="emit('download', item)" />
      <Button variant="ghost" icon="lucide-external-link" :aria-label="__('Open in New Tab')" :title="__('Open in New Tab')" @click="emit('tab', item)" />
      <Button variant="ghost" icon="lucide-x" :aria-label="__('Close')" :title="__('Close')" @click="emit('close')" />
    </div>

    <div class="relative flex min-h-0 flex-1 items-center justify-center overflow-auto bg-surface-gray-1">
      <img v-if="kind === 'image'" :key="item.id" :src="item.url" :alt="item.name" class="max-h-full max-w-full object-contain p-4" />
      <video v-else-if="kind === 'video'" :key="item.id" :src="item.url" controls autoplay class="max-h-full max-w-full" />
      <div v-else-if="kind === 'audio'" :key="item.id" class="flex w-full max-w-lg flex-col items-center gap-4 p-6">
        <span class="lucide-file-music size-16 text-ink-gray-5" aria-hidden="true" />
        <audio :src="item.url" controls autoplay class="w-full" />
      </div>
      <CloudPdf v-else-if="kind === 'pdf'" :node="item.id" />
      <iframe
        v-else-if="kind === 'markdown' && text !== null"
        :key="`md-${item.id}`"
        :srcdoc="page"
        sandbox=""
        :title="item.name"
        class="h-full w-full bg-surface-base [border:none]"
      />
      <pre v-else-if="kind === 'text' && text !== null" class="h-full w-full overflow-auto whitespace-pre-wrap break-words bg-surface-base p-4 font-mono text-sm text-ink-gray-8">{{ text }}</pre>
      <Loading v-else-if="kind && text === null" />
      <div v-else class="flex flex-col items-center gap-3 p-6 text-center">
        <span :class="[iconOf(item), inkOf(item)]" class="size-12" aria-hidden="true" />
        <span class="text-base text-ink-gray-7">{{ __("This file can't be shown here.") }}</span>
        <Button variant="solid" icon-left="lucide-download" :label="__('Download')" @click="emit('download', item)" />
      </div>
      <div v-if="cut" class="absolute bottom-3 start-1/2 -translate-x-1/2 rounded-full bg-surface-gray-3 px-3 py-1 text-sm text-ink-gray-7">
        {{ __("Showing the first {0}", [sizeText(MOST)]) }}
      </div>
    </div>
  </div>
  </Teleport>
</template>

<script setup>
// A file opened in One rather than a new tab: a picture, a video or a song
// played, a PDF drawn page by page, text and code as they are,
// Markdown as it reads (frappe's converter, in a frame that runs nothing),
// and the files beside it a step away with the arrows, the keys or a swipe.
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { Button, usePortalTarget } from "frappe-ui";

import { Loading, __, call } from "../kit";
import { API, iconOf, inkOf, sizeText, viewedAs } from "./cloud";
import { markdownPage } from "./frame";
import CloudPdf from "./CloudPdf.vue";

const props = defineProps({
  files: { type: Array, required: true },
  start: { type: String, required: true },
});
const emit = defineEmits(["close", "download", "tab", "moved"]);

const target = usePortalTarget();
const MOST = 2 * 1024 * 1024;
const root = ref(null);
const at = ref(Math.max(0, props.files.findIndex((one) => one.id === props.start)));
const item = computed(() => props.files[at.value] || null);
const kind = computed(() => viewedAs(item.value));
const text = ref(null);
const cut = ref(false);

const colors = ref({});
const page = computed(() => markdownPage(text.value, colors.value));

function readColors() {
  const look = root.value && getComputedStyle(root.value);
  if (look) colors.value = { ink: look.color, paper: look.backgroundColor, line: look.borderColor };
}

async function read() {
  text.value = null;
  cut.value = false;
  const one = item.value;
  if (!one || !["text", "markdown"].includes(kind.value)) return;
  const said = await call(API + "text", { node: one.id });
  if (one !== item.value) return;
  cut.value = said.cut;
  text.value = said.text;
}

watch(() => item.value?.id, () => {
  read();
  if (item.value) emit("moved", item.value);
});

function step(by) {
  const next = at.value + by;
  if (next >= 0 && next < props.files.length) at.value = next;
}

function key(event) {
  if (event.key === "Escape") return emit("close");
  if (event.target.closest?.("video, audio")) return;
  if (event.key === "ArrowLeft") step(document.dir === "rtl" ? 1 : -1);
  if (event.key === "ArrowRight") step(document.dir === "rtl" ? -1 : 1);
}

let touched = null;
const touchStart = (event) => (touched = event.changedTouches[0]?.clientX ?? null);
function touchEnd(event) {
  if (touched === null || kind.value === "pdf") return;
  const moved = (event.changedTouches[0]?.clientX ?? touched) - touched;
  touched = null;
  if (Math.abs(moved) > 60) step(moved < 0 ? 1 : -1);
}

onMounted(async () => {
  read();
  await nextTick();
  readColors();
  root.value?.focus();
});
</script>
