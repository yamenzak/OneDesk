<template>
  <div class="flex h-full min-h-0 w-full flex-col">
    <Loading v-if="!d.s.said || !lib" />
    <template v-else>
      <Toolbar :saving="saving" @save="save" />
      <div class="flex min-h-0 flex-1 flex-col overflow-y-auto md:flex-row md:overflow-hidden">
        <aside class="flex max-h-72 w-full shrink-0 flex-col border-b border-outline-gray-1 md:max-h-none md:w-60 md:border-b-0 md:border-e">
          <div class="flex items-center gap-1 px-3 pb-2 pt-3">
            <TabButtons v-model="tab" class="me-auto" :options="tabs" />
            <template v-if="tab === 'slides' && d.writable.value">
              <Button v-if="oneaiOn()" variant="ghost" size="sm" icon="lucide-sparkles" :tooltip="__('Design with OneAI')" :aria-label="__('Design with OneAI')" :loading="designing" @click="designWithAi" />
              <Button variant="ghost" size="sm" icon="lucide-plus" :tooltip="__('New Slide')" :aria-label="__('New Slide')" @click="addSlide" />
            </template>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto">
            <div v-if="tab === 'slides'" class="flex flex-col gap-1 px-2 pb-3">
              <button
                v-for="(one, i) in d.s.slides"
                :key="one.key"
                type="button"
                class="flex items-center gap-2 rounded-2 p-1.5 text-start"
                :class="one.key === d.s.picked ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-2'"
                @click="pick(one.key)"
              >
                <span class="w-4 shrink-0 text-center text-xs text-ink-gray-5">{{ i + 1 }}</span>
                <span class="relative h-9 w-16 shrink-0 overflow-hidden rounded-1 bg-surface-gray-3">
                  <span v-if="one.design" class="absolute left-0 top-0 origin-top-left" :style="thumb(one)" v-html="lib.slide(one.design, d.s.qrs)" />
                  <img v-else-if="one.kind === 'Image' && one.file" :src="one.file" class="h-full w-full object-cover" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm" :class="one.paused ? 'text-ink-gray-5' : 'text-ink-gray-8'">{{ one.title || __("Untitled") }}</span>
                  <span class="block truncate text-xs text-ink-gray-5">{{ kinds[one.kind] }} · {{ __("{0} seconds", [one.duration || 10]) }}</span>
                </span>
              </button>
              <p v-if="!d.s.slides.length" class="px-2 text-sm text-ink-gray-5">{{ __("No slides yet. Add one with the plus.") }}</p>
            </div>
            <Layers v-else />
          </div>
        </aside>

        <Canvas v-if="d.design.value" ref="canvas" :lib="lib" />
        <main v-else class="flex min-h-96 flex-1 items-center justify-center bg-surface-gray-2 p-6">
          <p v-if="!d.slide.value" class="text-base text-ink-gray-5">{{ __("Choose a slide, or add one.") }}</p>
          <img v-else-if="d.slide.value.kind === 'Image' && d.slide.value.file" :src="d.slide.value.file" class="max-h-full max-w-full" />
          <video v-else-if="d.slide.value.kind === 'Video' && d.slide.value.file" :src="d.slide.value.file" class="max-h-full max-w-full" muted controls />
          <div v-else-if="d.slide.value.kind === 'Design' && d.slide.value.html" class="relative aspect-video w-full max-w-4xl overflow-hidden">
            <iframe class="absolute left-0 top-0 h-full w-full border-0" sandbox="" :srcdoc="d.slide.value.html" />
          </div>
          <p v-else class="text-base text-ink-gray-5">{{ __("Nothing to show yet.") }}</p>
        </main>

        <Inspector @move="moveSlide" @remove="removeSlide" @canvas="toCanvas" @video="videoWithAi" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, TabButtons } from "frappe-ui";

import { Loading, __, alert, call, oneaiOn, onedesk, prompt, requires } from "../../kit";
import Canvas from "./Canvas.vue";
import Inspector from "./Inspector.vue";
import Layers from "./Layers.vue";
import Toolbar from "./Toolbar.vue";
import { makeDesigner, newId } from "./store";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
});

const API = "onedesk.one_display.slides.";
const RENDERER = "/assets/onedesk/js/one_display/blocks.js";
const d = makeDesigner();
const lib = ref(null);
const tab = ref("slides");
const saving = ref(false);
const designing = ref(false);
const canvas = ref(null);

const name = computed(() => props.route[0] || props.query.playlist || "");
const kinds = { Image: __("Image"), Video: __("Video"), "Web Page": __("Web Page"), Design: __("Design") };
const tabs = [
  { label: __("Slides"), value: "slides" },
  { label: __("Layers"), value: "layers" },
];

const thumb = (one) => {
  const tall = one.design.orientation === "Portrait";
  const [w, h] = tall ? [1080, 1920] : [1920, 1080];
  const k = Math.min(64 / w, 36 / h);
  return { width: `${w}px`, height: `${h}px`, transform: `scale(${k})` };
};

function adopt(data, keep = false) {
  const was = d.s.picked;
  d.s.said = data;
  d.s.schema = data.schema;
  d.s.slides = data.slides.map((one) => ({ ...one, key: one.id || newId("s") }));
  d.s.picked = keep && d.s.slides.some((one) => one.key === was) ? was : d.s.slides[0]?.key || null;
  if (!keep) d.s.chosen = [];
  d.s.dirty = false;
  d.s.past = [];
  d.s.future = [];
}

function pick(key) {
  d.s.picked = key;
  d.choose([]);
  if (tab.value === "layers" && !d.design.value) tab.value = "slides";
}

function addSlide() {
  d.remember();
  const one = { key: newId("s"), id: null, kind: "Design", title: "", duration: 10, paused: 0, design: d.blank() };
  d.s.slides.push(one);
  pick(one.key);
}

function removeSlide() {
  const at = d.s.slides.findIndex((one) => one.key === d.s.picked);
  if (at < 0) return;
  d.remember();
  d.s.slides.splice(at, 1);
  d.s.picked = d.s.slides[Math.min(at, d.s.slides.length - 1)]?.key || null;
  d.choose([]);
}

function moveSlide(by) {
  const at = d.s.slides.findIndex((one) => one.key === d.s.picked);
  const to = at + by;
  if (at < 0 || to < 0 || to >= d.s.slides.length) return;
  d.remember();
  const [one] = d.s.slides.splice(at, 1);
  d.s.slides.splice(to, 0, one);
}

function toCanvas() {
  d.remember();
  d.slide.value.design = d.blank();
  d.slide.value.html = null;
}

// Every QR code on every slide, drawn by the server once per address.
let asking = null;
watch(
  () => d.s.slides.flatMap((one) => (one.design?.blocks || []).filter((b) => b.kind === "qr" && b.link).map((b) => b.link)),
  (links) => {
    clearTimeout(asking);
    asking = setTimeout(async () => {
      for (const link of new Set(links)) {
        if (link in d.s.qrs) continue;
        d.s.qrs = { ...d.s.qrs, [link]: await call(API + "qr", { link }) };
      }
    }, 400);
  },
  { immediate: true },
);

function designWithAi() {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), reqd: 1 }],
    async ({ description }) => {
      designing.value = true;
      try {
        const made = await call("onedesk.one_display.make.design", { description, orientation: d.design.value?.orientation || "Landscape" });
        d.remember();
        const one = { key: newId("s"), id: null, kind: "Design", title: description.slice(0, 140), duration: 12, paused: 0, design: made.design };
        d.s.slides.push(one);
        pick(one.key);
      } finally {
        designing.value = false;
      }
    },
    __("Design a Slide"),
    __("Design"),
  );
}

// A video takes OneAI minutes, so it is made in the background and arrives as
// a paused slide at the end; whoever asked is told.
function videoWithAi() {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows"), reqd: 1 }],
    async ({ description }) => {
      await call("onedesk.one_display.make.video", { playlist: name.value, description, orientation: d.portrait.value ? "Portrait" : "Landscape" });
      alert(__("OneAI is making the video. You will be told when it is in the playlist."), "blue");
    },
    __("Make a Video with OneAI"),
    __("Make"),
  );
}

async function save() {
  if (!d.writable.value || saving.value) return;
  saving.value = true;
  try {
    const sent = d.s.slides.map(({ key, ...one }) => one);
    const loaded = d.s.said.slides.map((one) => one.id);
    const picked = d.s.slides.findIndex((one) => one.key === d.s.picked);
    const chosen = [...d.s.chosen];
    adopt(await call(API + "save", { playlist: name.value, slides: JSON.stringify(sent), loaded: JSON.stringify(loaded) }));
    d.s.picked = d.s.slides[Math.max(picked, 0)]?.key || null;
    d.s.chosen = chosen.filter((id) => d.blocks.value.some((one) => one.id === id));
  } finally {
    saving.value = false;
  }
}

const typing = (el) => ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable;

function keys(event) {
  const mod = event.ctrlKey || event.metaKey;
  const key = event.key.toLowerCase();
  if (mod && key === "s") return event.preventDefault(), save();
  if (typing(event.target)) return;
  if (mod && key === "z") return event.preventDefault(), event.shiftKey ? d.redo() : d.undo();
  if (mod && key === "y") return event.preventDefault(), d.redo();
  if (!d.design.value || !d.writable.value) return;
  if (mod && key === "a") return event.preventDefault(), d.choose(d.blocks.value.filter((one) => !one.hidden && !one.locked).map((one) => one.id));
  if (mod && key === "c") return d.copy();
  if (mod && key === "v") return event.preventDefault(), d.paste();
  if (mod && key === "d") return event.preventDefault(), d.duplicate();
  if (mod && key === "]") return event.preventDefault(), d.restack(event.shiftKey ? "front" : "forward");
  if (mod && key === "[") return event.preventDefault(), d.restack(event.shiftKey ? "back" : "backward");
  if (key === "escape") return d.choose([]);
  if (!d.chosenBlocks.value.length) return;
  if (key === "delete" || key === "backspace") return event.preventDefault(), d.remove();
  if (key === "enter" && d.only.value?.kind === "text") return event.preventDefault(), canvas.value?.edit(d.only.value);
  const step = event.shiftKey ? 5 : 0.5;
  const moves = { arrowleft: ["x", -step], arrowright: ["x", step], arrowup: ["y", -step], arrowdown: ["y", step] };
  if (!moves[key]) return;
  event.preventDefault();
  const [axis, by] = moves[key];
  d.remember("nudge");
  for (const one of d.chosenBlocks.value) if (!one.locked) one[axis] = Math.round((one[axis] + by) * 100) / 100;
}

onMounted(async () => {
  const [data] = await Promise.all([call(API + "get", { playlist: name.value }), requires(RENDERER)]);
  lib.value = onedesk().blocks;
  adopt(data);
  document.addEventListener("keydown", keys);
});

onBeforeUnmount(() => document.removeEventListener("keydown", keys));
</script>
