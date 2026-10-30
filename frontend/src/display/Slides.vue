<template>
  <div class="flex h-full min-h-0 w-full flex-col overflow-y-auto md:flex-row md:overflow-hidden">
    <aside class="flex max-h-56 w-full md:max-h-none md:w-60 shrink-0 flex-col border-b md:border-b-0 md:border-e border-outline-gray-1">
      <div class="flex items-center gap-1 p-3 pb-2">
        <h3 class="me-auto text-sm font-medium text-ink-gray-5">{{ __("Slides") }}</h3>
        <Button v-if="said?.writable && oneaiOn()" variant="ghost" icon="lucide-sparkles" :title="__('Design with OneAI')" :aria-label="__('Design with OneAI')" :loading="designing" @click="designWithAi" />
        <Button v-if="said?.writable" variant="ghost" icon="lucide-plus" :title="__('New Slide')" :aria-label="__('New Slide')" @click="addSlide" />
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        <button
          v-for="(one, i) in slides"
          :key="one.key"
          class="mb-1 flex w-full items-center gap-2 rounded-2 px-2 py-1.5 text-start"
          :class="one.key === picked ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-2'"
          @click="pick(one.key)"
        >
          <span class="w-5 shrink-0 text-sm text-ink-gray-5">{{ i + 1 }}</span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-base text-ink-gray-8">{{ one.title || kinds[one.kind] }}</span>
            <span class="block truncate text-sm text-ink-gray-5">{{ kinds[one.kind] }} · {{ __("{0} seconds", [one.duration || 10]) }}</span>
          </span>
        </button>
        <p v-if="said && !slides.length" class="px-2 text-sm text-ink-gray-5">{{ __("No slides yet. Add one with the plus.") }}</p>
      </div>
    </aside>

    <main class="flex h-96 min-w-0 shrink-0 flex-col md:h-auto md:flex-1 md:shrink">
      <div class="flex flex-wrap items-center gap-2 border-b border-outline-gray-1 px-4 py-2">
        <template v-if="design && said?.writable">
          <Button :label="__('Text')" icon-left="lucide-type" @click="addBlock('text')" />
          <Button :label="__('Picture')" icon-left="lucide-image" @click="addBlock('image')" />
          <Button :label="__('Shape')" icon-left="lucide-square" @click="addBlock('shape')" />
          <Button :label="__('QR Code')" icon-left="lucide-qr-code" @click="addBlock('qr')" />
        </template>
        <span class="flex-1" />
        <Button variant="solid" :label="__('Save')" :loading="saving" :disabled="!dirty || !said?.writable" @click="save" />
      </div>
      <div ref="area" class="flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-surface-gray-2 p-6">
        <Loading v-if="!said" />
        <p v-else-if="!slide" class="text-base text-ink-gray-5">{{ __("Choose a slide, or add one.") }}</p>
        <div v-else ref="stage" class="relative overflow-hidden" :style="stageStyle" @pointerdown.self="block = null">
          <template v-if="design">
            <div
              v-for="one in design.blocks"
              :key="one.id"
              class="absolute select-none"
              :class="said.writable ? 'cursor-move' : ''"
              :style="blockStyle(one)"
              @pointerdown.stop="grab($event, one, 'move')"
            >
              <img v-if="one.kind === 'image' && one.src" :src="one.src" class="block h-full w-full" :style="{ objectFit: one.fit }" />
              <div v-else-if="one.kind === 'qr'" class="h-full w-full" v-html="qrs[one.link] || ''" />
              <template v-else-if="one.kind === 'text'">{{ one.text || __("Text") }}</template>
              <span v-if="one.kind === 'image' && !one.src" class="flex h-full w-full items-center justify-center bg-surface-gray-3 text-ink-gray-5">
                {{ __("Picture") }}
              </span>
              <span
                class="pointer-events-none absolute inset-0 border border-dashed"
                :class="one.id === block ? 'border-outline-gray-5' : 'border-transparent'"
              />
              <span
                v-if="one.id === block && said.writable"
                class="absolute bottom-0 end-0 h-3 w-3 cursor-se-resize rounded-1 bg-surface-gray-7"
                @pointerdown.stop="grab($event, one, 'size')"
              />
            </div>
          </template>
          <template v-else-if="slide.kind === 'Design'">
            <iframe class="pointer-events-none absolute start-0 top-0 border-0" :style="codeStyle" :srcdoc="codeDoc" sandbox="" />
          </template>
          <img v-else-if="slide.kind === 'Image' && slide.file" :src="slide.file" class="h-full w-full" :style="{ objectFit: slide.fit === 'Contain' ? 'contain' : 'cover' }" />
          <video v-else-if="slide.kind === 'Video' && slide.file" :src="slide.file" class="h-full w-full" muted controls />
          <p v-else class="flex h-full items-center justify-center p-6 text-center text-base text-ink-gray-4">{{ slide.url || __("Nothing to show yet.") }}</p>
        </div>
      </div>
    </main>

    <aside class="w-full shrink-0 border-t border-outline-gray-1 p-4 md:w-80 md:overflow-y-auto md:border-s md:border-t-0">
      <div v-if="current" class="flex flex-col gap-3">
        <div class="flex items-center gap-1">
          <span class="me-auto text-base font-medium text-ink-gray-8">{{ blockKinds[current.kind] }}</span>
          <Button variant="ghost" icon="lucide-arrow-up" :title="__('Bring Forward')" :aria-label="__('Bring Forward')" @click="layer(1)" />
          <Button variant="ghost" icon="lucide-arrow-down" :title="__('Send Back')" :aria-label="__('Send Back')" @click="layer(-1)" />
          <Button variant="ghost" icon="lucide-trash-2" :title="__('Remove')" :aria-label="__('Remove')" @click="removeBlock" />
        </div>
        <div class="grid grid-cols-4 gap-2">
          <FormControl v-for="key in ['x', 'y', 'w', 'h']" :key="key" v-model.number="current[key]" :label="edges[key]" type="number" @update:model-value="touch" />
        </div>

        <template v-if="current.kind === 'text'">
          <FormControl v-model="current.text" :label="__('Words')" type="textarea" :rows="3" @update:model-value="touch" />
          <div class="grid grid-cols-2 gap-2">
            <FormControl v-model.number="current.size" :label="__('Size')" type="number" @update:model-value="touch" />
            <FormControl v-model.number="current.weight" :label="__('Weight')" type="select" :options="weights" @update:model-value="touch" />
          </div>
          <div class="flex items-end gap-2">
            <FormControl v-model="current.colour" class="flex-1" :label="__('Colour')" type="text" @update:model-value="touch" />
            <span class="mb-1 h-6 w-6 shrink-0 rounded-2 border border-outline-gray-2" :style="{ background: current.colour }" />
          </div>
          <FormControl v-model="current.align" :label="__('Align')" type="select" :options="aligns" @update:model-value="touch" />
          <div class="grid grid-cols-2 gap-2">
            <FormControl v-model.number="current.line" :label="__('Line Height')" type="number" step="0.05" @update:model-value="touch" />
            <FormControl v-model.number="current.spacing" :label="__('Letter Spacing')" type="number" step="0.01" @update:model-value="touch" />
          </div>
          <FormControl :model-value="Boolean(current.upper)" :label="__('Capitals')" type="checkbox" @update:model-value="(v) => ((current.upper = v ? 1 : 0), touch())" />
        </template>

        <template v-else-if="current.kind === 'image'">
          <img v-if="current.src" :src="current.src" class="max-h-28 self-start rounded-2" />
          <div class="flex gap-2">
            <Button :label="__('Upload')" icon-left="lucide-upload" @click="uploadTo(current, 'src', 'image/*')" />
            <Button v-if="oneaiOn()" :label="__('Make with OneAI')" icon-left="lucide-sparkles" :loading="drawing" @click="pictureWithAi(current)" />
          </div>
          <FormControl v-model="current.fit" :label="__('Fit')" type="select" :options="fits" @update:model-value="touch" />
          <FormControl v-model.number="current.radius" :label="__('Corners')" type="number" @update:model-value="touch" />
        </template>

        <template v-else-if="current.kind === 'shape'">
          <div class="flex items-end gap-2">
            <FormControl v-model="current.fill" class="flex-1" :label="__('Colour')" type="text" @update:model-value="touch" />
            <span class="mb-1 h-6 w-6 shrink-0 rounded-2 border border-outline-gray-2" :style="{ background: current.fill }" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <FormControl v-model.number="current.radius" :label="__('Corners')" type="number" @update:model-value="touch" />
            <FormControl v-model.number="current.opacity" :label="__('Opacity')" type="number" step="0.05" @update:model-value="touch" />
          </div>
        </template>

        <template v-else-if="current.kind === 'qr'">
          <FormControl v-model="current.link" :label="__('Address')" type="text" @update:model-value="touchCode(current)" />
        </template>
      </div>

      <div v-else-if="slide" class="flex flex-col gap-3">
        <div class="flex items-center gap-1">
          <span class="me-auto text-base font-medium text-ink-gray-8">{{ __("Slide") }}</span>
          <Button variant="ghost" icon="lucide-arrow-up" :title="__('Move Up')" :aria-label="__('Move Up')" @click="moveSlide(-1)" />
          <Button variant="ghost" icon="lucide-arrow-down" :title="__('Move Down')" :aria-label="__('Move Down')" @click="moveSlide(1)" />
          <Button variant="ghost" icon="lucide-trash-2" :title="__('Remove')" :aria-label="__('Remove')" @click="removeSlide" />
        </div>
        <FormControl v-model="slide.title" :label="__('Title')" type="text" @update:model-value="touch" />
        <FormControl v-model="slide.kind" :label="__('Kind')" type="select" :options="kindOptions" @update:model-value="kindChanged" />
        <FormControl v-model.number="slide.duration" :label="__('Seconds')" type="number" @update:model-value="touch" />

        <template v-if="design">
          <FormControl v-model="design.orientation" :label="__('Orientation')" type="select" :options="orientations" @update:model-value="touch" />
          <div class="flex items-end gap-2">
            <FormControl v-model="design.background" class="flex-1" :label="__('Background')" type="text" @update:model-value="touch" />
            <span class="mb-1 h-6 w-6 shrink-0 rounded-2 border border-outline-gray-2" :style="{ background: design.background }" />
          </div>
          <div class="flex gap-2">
            <Button :label="__('Background Picture')" icon-left="lucide-image" @click="uploadTo(design, 'image', 'image/*')" />
            <Button v-if="design.image" variant="ghost" icon="lucide-x" :title="__('Remove')" :aria-label="__('Remove')" @click="((design.image = ''), touch())" />
          </div>
        </template>
        <div v-else-if="slide.kind === 'Design'" class="flex flex-col gap-2">
          <p class="text-sm text-ink-gray-5">{{ __("This slide was written as code, so it is shown here but can't be moved block by block.") }}</p>
          <Button :label="__('Start Again on the Canvas')" icon-left="lucide-pen-tool" @click="toCanvas" />
        </div>
        <template v-else-if="slide.kind === 'Image' || slide.kind === 'Video'">
          <Button :label="__('Upload')" icon-left="lucide-upload" @click="uploadTo(slide, 'file', slide.kind === 'Image' ? 'image/*' : 'video/*')" />
          <FormControl v-if="slide.kind === 'Image'" v-model="slide.fit" :label="__('Fit')" type="select" :options="slideFits" @update:model-value="touch" />
          <Button v-if="slide.kind === 'Video' && oneaiOn()" :label="__('Make a Video with OneAI')" icon-left="lucide-sparkles" :loading="filming" @click="videoWithAi" />
        </template>
        <FormControl v-else-if="slide.kind === 'Web Page'" v-model="slide.url" :label="__('Address')" type="text" placeholder="https://" @update:model-value="touch" />

        <FormControl v-model="slide.paused" :label="__('Paused')" type="checkbox" @update:model-value="touch" />
        <div class="grid grid-cols-2 gap-2">
          <FormControl v-model="slide.from_date" :label="__('Shown From')" type="date" @update:model-value="touch" />
          <FormControl v-model="slide.to_date" :label="__('Shown Until')" type="date" @update:model-value="touch" />
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, FormControl } from "frappe-ui";

import { Loading, __, alert, call, oneaiOn, prompt, upload } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
});

const API = "onedesk.one_display.slides.";
const said = ref(null);
const slides = ref([]);
const picked = ref(null);
const block = ref(null);
const dirty = ref(false);
const saving = ref(false);
const designing = ref(false);
const drawing = ref(false);
const filming = ref(false);
const qrs = ref({});
const area = ref(null);
const stage = ref(null);
const room = ref({ w: 960, h: 540 });
let seq = 0;

const name = computed(() => props.route[0] || props.query.playlist || "");
const kinds = { Image: __("Image"), Video: __("Video"), "Web Page": __("Web Page"), Design: __("Design") };
const kindOptions = Object.entries(kinds).map(([value, label]) => ({ label, value }));
const blockKinds = { text: __("Text"), image: __("Picture"), shape: __("Shape"), qr: __("QR Code") };
const orientations = [
  { label: __("Landscape"), value: "Landscape" },
  { label: __("Portrait"), value: "Portrait" },
];
const edges = { x: __("Left"), y: __("Top"), w: __("Width"), h: __("Height") };
const weights = [
  { label: __("Regular"), value: 400 },
  { label: __("Semibold"), value: 600 },
  { label: __("Bold"), value: 700 },
  { label: __("Heavy"), value: 800 },
];
const aligns = [
  { label: __("Start"), value: "start" },
  { label: __("Centre"), value: "center" },
  { label: __("End"), value: "end" },
];
const fits = [
  { label: __("Fill"), value: "cover" },
  { label: __("Fit Inside"), value: "contain" },
];
const slideFits = [
  { label: __("Fill"), value: "Cover" },
  { label: __("Fit Inside"), value: "Contain" },
];

const slide = computed(() => slides.value.find((one) => one.key === picked.value) || null);
const design = computed(() => (slide.value?.kind === "Design" ? slide.value.design : null));
const current = computed(() => design.value?.blocks.find((one) => one.id === block.value) || null);
const portrait = computed(() => design.value?.orientation === "Portrait");
const width = computed(() => (portrait.value ? 1080 : 1920));

const frame = computed(() => {
  const ratio = portrait.value ? 9 / 16 : 16 / 9;
  const w = Math.min(room.value.w, room.value.h * ratio);
  return { w, h: w / ratio };
});
const scale = computed(() => frame.value.w / width.value);
const stageStyle = computed(() => {
  const ground = design.value
    ? { background: design.value.background, backgroundImage: design.value.image ? `url('${design.value.image}')` : "none", backgroundSize: "cover", backgroundPosition: "center" }
    : {};
  return { width: `${frame.value.w}px`, height: `${frame.value.h}px`, ...ground };
});
const codeStyle = computed(() => ({ width: "1920px", height: "1080px", transform: `scale(${frame.value.w / 1920})`, transformOrigin: "0 0" }));
const codeDoc = computed(() => `<body style='margin:0;position:relative;width:1920px;height:1080px;overflow:hidden'>${slide.value?.html || ""}</body>`);

function blockStyle(one) {
  const box = { left: `${one.x}%`, top: `${one.y}%`, width: `${one.w}%`, height: `${one.h}%`, overflow: "hidden" };
  if (one.kind === "text") {
    return {
      ...box,
      color: one.colour,
      fontSize: `${one.size * scale.value}px`,
      fontWeight: one.weight,
      lineHeight: one.line,
      textAlign: one.align,
      letterSpacing: `${one.spacing}em`,
      textTransform: one.upper ? "uppercase" : "none",
      whiteSpace: "pre-wrap",
      overflowWrap: "break-word",
    };
  }
  if (one.kind === "shape") return { ...box, background: one.fill, borderRadius: `${one.radius * scale.value}px`, opacity: one.opacity };
  if (one.kind === "image") return { ...box, borderRadius: `${one.radius * scale.value}px` };
  return box;
}

function adopt(data) {
  said.value = data;
  slides.value = data.slides.map((one) => ({ ...one, key: one.id }));
  if (!slides.value.some((one) => one.key === picked.value)) picked.value = slides.value[0]?.key || null;
  block.value = null;
  dirty.value = false;
  slides.value.forEach((one) => one.design?.blocks.forEach((b) => b.kind === "qr" && code(b.link)));
}

async function load() {
  adopt(await call(API + "get", { playlist: name.value }));
}

function measure() {
  if (!area.value) return;
  const rect = area.value.getBoundingClientRect();
  room.value = { w: Math.max(rect.width - 48, 200), h: Math.max(rect.height - 48, 120) };
}

const touch = () => (dirty.value = true);

function pick(key) {
  picked.value = key;
  block.value = null;
}

function blankDesign() {
  return { orientation: "Landscape", background: said.value.ground, image: "", blocks: [] };
}

function addSlide() {
  const one = { key: `new-${++seq}`, id: null, kind: "Design", title: "", duration: 10, design: blankDesign() };
  slides.value.push(one);
  pick(one.key);
  touch();
}

function removeSlide() {
  const at = slides.value.findIndex((one) => one.key === picked.value);
  slides.value.splice(at, 1);
  picked.value = slides.value[Math.min(at, slides.value.length - 1)]?.key || null;
  touch();
}

function moveSlide(by) {
  const at = slides.value.findIndex((one) => one.key === picked.value);
  const to = at + by;
  if (to < 0 || to >= slides.value.length) return;
  const [one] = slides.value.splice(at, 1);
  slides.value.splice(to, 0, one);
  touch();
}

function kindChanged() {
  if (slide.value.kind === "Design" && !slide.value.design && !slide.value.html) slide.value.design = blankDesign();
  block.value = null;
  touch();
}

function toCanvas() {
  slide.value.design = blankDesign();
  slide.value.html = null;
  touch();
}

const SIZES = { text: [60, 18], image: [30, 40], shape: [40, 30], qr: [14, 25] };

function addBlock(kind) {
  const [w, h] = SIZES[kind];
  const one = { ...said.value.defaults[kind], id: `b${Date.now().toString(36)}${++seq}`, kind, x: (100 - w) / 2, y: (100 - h) / 2, w, h };
  if (kind === "text") one.text = __("Your words here");
  design.value.blocks.push(one);
  block.value = one.id;
  touch();
}

function removeBlock() {
  design.value.blocks = design.value.blocks.filter((one) => one.id !== block.value);
  block.value = null;
  touch();
}

function layer(by) {
  const list = design.value.blocks;
  const at = list.findIndex((one) => one.id === block.value);
  const to = at + by;
  if (to < 0 || to >= list.length) return;
  const [one] = list.splice(at, 1);
  list.splice(to, 0, one);
  touch();
}

const clamp = (v, low, high) => Math.min(Math.max(v, low), high);
const snap = (v) => Math.round(v * 2) / 2;

function grab(event, one, how) {
  block.value = one.id;
  if (!said.value.writable) return;
  const rect = stage.value.getBoundingClientRect();
  const start = { x: event.clientX, y: event.clientY, one: { ...one } };
  const move = (e) => {
    const dx = ((e.clientX - start.x) / rect.width) * 100;
    const dy = ((e.clientY - start.y) / rect.height) * 100;
    if (how === "move") {
      one.x = snap(clamp(start.one.x + dx, 0, 100 - one.w));
      one.y = snap(clamp(start.one.y + dy, 0, 100 - one.h));
    } else {
      one.w = snap(clamp(start.one.w + dx, 0.5, 100 - one.x));
      one.h = snap(clamp(start.one.h + dy, 0.5, 100 - one.y));
    }
    touch();
  };
  const up = () => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", up);
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
}

function nudge(event) {
  if (!current.value || ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
  if (event.key === "Delete" || event.key === "Backspace") return removeBlock();
  const step = event.shiftKey ? 5 : 0.5;
  const moves = { ArrowLeft: ["x", -step], ArrowRight: ["x", step], ArrowUp: ["y", -step], ArrowDown: ["y", step] };
  const move = moves[event.key];
  if (!move) return;
  event.preventDefault();
  const [key, by] = move;
  const limit = key === "x" ? 100 - current.value.w : 100 - current.value.h;
  current.value[key] = clamp(current.value[key] + by, 0, limit);
  touch();
}

let coding = null;
async function code(link) {
  if (!link || link in qrs.value) return;
  qrs.value = { ...qrs.value, [link]: await call(API + "qr", { link }) };
}

function touchCode(one) {
  touch();
  clearTimeout(coding);
  coding = setTimeout(() => code(one.link), 500);
}

function uploadTo(target, key, types) {
  upload(null, null, (file) => ((target[key] = file.file_url), touch()), {
    allow_multiple: false,
    make_attachments_public: true,
    restrictions: { allowed_file_types: [types] },
  });
}

function designWithAi() {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), reqd: 1 }],
    async ({ description }) => {
      designing.value = true;
      try {
        const made = await call("onedesk.one_display.make.design", { description, orientation: design.value?.orientation || "Landscape" });
        const one = { key: `new-${++seq}`, id: null, kind: "Design", title: description.slice(0, 140), duration: 12, design: made.design };
        one.design.blocks.forEach((b) => b.kind === "qr" && code(b.link));
        slides.value.push(one);
        pick(one.key);
        touch();
      } finally {
        designing.value = false;
      }
    },
    __("Design a Slide"),
    __("Design"),
  );
}

function pictureWithAi(one) {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows"), reqd: 1 }],
    async ({ description }) => {
      drawing.value = true;
      try {
        one.src = await call("onedesk.one_display.make.picture", { description });
        touch();
      } finally {
        drawing.value = false;
      }
    },
    __("Make a Picture"),
    __("Make"),
  );
}

// A video takes OneAI minutes, so it is made in the background and arrives as
// a paused slide at the end; whoever asked is told.
function videoWithAi() {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows"), reqd: 1 }],
    async ({ description }) => {
      filming.value = true;
      try {
        await call("onedesk.one_display.make.video", { playlist: name.value, description, orientation: portrait.value ? "Portrait" : "Landscape" });
        alert(__("OneAI is making the video. You will be told when it is in the playlist."), "blue");
      } finally {
        filming.value = false;
      }
    },
    __("Make a Video with OneAI"),
    __("Make"),
  );
}

async function save() {
  saving.value = true;
  try {
    const sent = slides.value.map(({ key, ...one }) => one);
    const loaded = said.value.slides.map((one) => one.id);
    adopt(await call(API + "save", { playlist: name.value, slides: JSON.stringify(sent), loaded: JSON.stringify(loaded) }));
  } finally {
    saving.value = false;
  }
}

watch(picked, () => (block.value = null));

let observer = null;
onMounted(async () => {
  await load();
  measure();
  observer = new ResizeObserver(measure);
  if (area.value) observer.observe(area.value);
  document.addEventListener("keydown", nudge);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  document.removeEventListener("keydown", nudge);
});
</script>
