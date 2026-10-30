<template>
  <div ref="area" class="relative min-h-0 flex-1 overflow-auto bg-surface-gray-2" @pointerdown="sweep">
    <div class="flex min-h-full min-w-max items-center justify-center p-8">
      <div ref="sheet" class="relative shrink-0 select-none" :style="{ width: `${paper.w}px`, height: `${paper.h}px` }">
        <div class="pointer-events-none absolute left-0 top-0 origin-top-left" :style="stageStyle" v-html="html" />

        <div v-if="editing" class="absolute left-0 top-0 origin-top-left" :style="stageStyle">
          <div ref="editor" contenteditable="plaintext-only" :style="editStyle" @blur="finish" @keydown.esc.prevent="finish" @pointerdown.stop />
        </div>

        <div
          v-for="one in shown"
          :key="one.id"
          class="absolute hover:ring-1 hover:ring-outline-blue-5"
          :class="one.locked || !d.writable.value ? 'cursor-default' : 'cursor-move'"
          :style="box(one)"
          @pointerdown.stop="grab($event, one)"
          @dblclick.stop="edit(one)"
        >
          <span
            v-if="(one.kind === 'image' && !one.src) || (one.kind === 'qr' && !one.link)"
            class="flex h-full w-full items-center justify-center border border-dashed border-outline-gray-4 bg-surface-gray-3 text-sm text-ink-gray-6"
          >
            {{ one.kind === "image" ? __("Picture") : __("QR Code") }}
          </span>
        </div>

        <div v-for="one in d.chosenBlocks.value" :key="`c-${one.id}`" class="pointer-events-none absolute border border-outline-blue-5" :style="box(one)">
          <template v-if="lone && !one.locked && d.writable.value && d.s.editing !== one.id">
            <span
              v-for="h in HANDLES"
              :key="h.at"
              class="pointer-events-auto absolute h-2.5 w-2.5 rounded-1 border border-outline-blue-5 bg-surface-base"
              :class="h.cls"
              @pointerdown.stop="resize($event, one, h.at)"
            />
            <span class="absolute left-1/2 -top-6 h-6 w-px bg-surface-blue-5" />
            <span
              class="pointer-events-auto absolute left-1/2 -top-8 h-3 w-3 -translate-x-1/2 cursor-grab rounded-full border border-outline-blue-5 bg-surface-base"
              :title="__('Rotate')"
              @pointerdown.stop="turn($event, one)"
            />
          </template>
        </div>

        <span v-for="(g, i) in guides" :key="`g-${i}`" class="pointer-events-none absolute bg-surface-blue-5" :style="guideStyle(g)" />
        <span v-if="band" class="pointer-events-none absolute border border-outline-blue-5 bg-surface-blue-2 opacity-60" :style="bandStyle" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import { __ } from "../../kit";
import { round, useDesigner } from "./store";

const props = defineProps({ lib: { type: Object, required: true } });
const d = useDesigner();

const area = ref(null);
const sheet = ref(null);
const room = ref({ w: 960, h: 540 });
const editor = ref(null);
const guides = ref([]);
const band = ref(null);

const HANDLES = [
  { at: "nw", cls: "-left-1.5 -top-1.5 cursor-nwse-resize" },
  { at: "n", cls: "left-1/2 -top-1.5 -translate-x-1/2 cursor-ns-resize" },
  { at: "ne", cls: "-right-1.5 -top-1.5 cursor-nesw-resize" },
  { at: "e", cls: "-right-1.5 top-1/2 -translate-y-1/2 cursor-ew-resize" },
  { at: "se", cls: "-bottom-1.5 -right-1.5 cursor-nwse-resize" },
  { at: "s", cls: "-bottom-1.5 left-1/2 -translate-x-1/2 cursor-ns-resize" },
  { at: "sw", cls: "-bottom-1.5 -left-1.5 cursor-nesw-resize" },
  { at: "w", cls: "-left-1.5 top-1/2 -translate-y-1/2 cursor-ew-resize" },
];
const NEAR = 6;

const scale = computed(() => {
  const { w, h } = d.size.value;
  if (d.s.zoom !== "fit") return Number(d.s.zoom);
  return Math.max(Math.min((room.value.w - 64) / w, (room.value.h - 64) / h), 0.05);
});
const paper = computed(() => ({ w: d.size.value.w * scale.value, h: d.size.value.h * scale.value }));
const stageStyle = computed(() => ({ width: `${d.size.value.w}px`, height: `${d.size.value.h}px`, transform: `scale(${scale.value})` }));
const shown = computed(() => d.blocks.value.filter((one) => !one.hidden));
const lone = computed(() => d.chosenBlocks.value.length === 1);
const editing = computed(() => d.blocks.value.find((one) => one.id === d.s.editing) || null);

const html = computed(() => {
  const design = d.design.value;
  if (!design) return "";
  const blocks = design.blocks.map((one) => (one.id === d.s.editing ? { ...one, hidden: 1 } : one));
  return props.lib.slide({ ...design, blocks }, d.s.qrs);
});
const editStyle = computed(() => (editing.value ? `${props.lib.style(editing.value)}white-space:pre-wrap;word-wrap:break-word;outline:none;cursor:text;` : ""));

const box = (one) => ({ left: `${one.x}%`, top: `${one.y}%`, width: `${one.w}%`, height: `${one.h}%`, transform: one.rotate ? `rotate(${one.rotate}deg)` : "" });
const guideStyle = (g) => (g.axis === "x" ? { left: `${g.at}%`, top: 0, width: "1px", height: "100%" } : { top: `${g.at}%`, left: 0, height: "1px", width: "100%" });
const bandStyle = computed(() => {
  const b = band.value;
  return { left: `${Math.min(b.x0, b.x1)}px`, top: `${Math.min(b.y0, b.y1)}px`, width: `${Math.abs(b.x1 - b.x0)}px`, height: `${Math.abs(b.y1 - b.y0)}px` };
});

function measure() {
  if (!area.value) return;
  room.value = { w: area.value.clientWidth, h: area.value.clientHeight };
}

// Where the edges and middles of the slide and the other blocks are, for a
// moving block to settle on.
function lines(moving) {
  const xs = [0, 50, 100];
  const ys = [0, 50, 100];
  for (const one of shown.value) {
    if (moving.includes(one.id) || one.rotate) continue;
    xs.push(one.x, one.x + one.w / 2, one.x + one.w);
    ys.push(one.y, one.y + one.h / 2, one.y + one.h);
  }
  return { xs, ys };
}

function settle(edges, targets, near) {
  let best = null;
  for (const edge of edges)
    for (const at of targets) {
      const by = at - edge;
      if (Math.abs(by) <= near && (!best || Math.abs(by) < Math.abs(best.by))) best = { by, at };
    }
  return best;
}

function follow(move, done) {
  const up = () => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", up);
    guides.value = [];
    done?.();
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
}

function grab(event, one) {
  if (d.s.editing === one.id) return;
  const adding = event.shiftKey || event.metaKey || event.ctrlKey;
  if (adding || !d.s.chosen.includes(one.id)) d.choose(one.id, adding);
  if (!d.writable.value || adding) return;
  const moving = d.chosenBlocks.value.filter((b) => !b.locked);
  if (!moving.length) return;
  const start = { x: event.clientX, y: event.clientY, at: moving.map((b) => ({ b, x: b.x, y: b.y })) };
  const ids = moving.map((b) => b.id);
  const targets = lines(ids);
  let begun = false;
  follow((e) => {
    const dx = ((e.clientX - start.x) / paper.value.w) * 100;
    const dy = ((e.clientY - start.y) / paper.value.h) * 100;
    if (!begun && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 3) return;
    if (!begun) d.remember(), (begun = true);
    let mx = dx;
    let my = dy;
    guides.value = [];
    if (!e.altKey) {
      const left = Math.min(...start.at.map((s) => s.x)) + dx;
      const right = Math.max(...start.at.map((s) => s.x + s.b.w)) + dx;
      const top = Math.min(...start.at.map((s) => s.y)) + dy;
      const bottom = Math.max(...start.at.map((s) => s.y + s.b.h)) + dy;
      const sx = settle([left, (left + right) / 2, right], targets.xs, (NEAR / paper.value.w) * 100);
      const sy = settle([top, (top + bottom) / 2, bottom], targets.ys, (NEAR / paper.value.h) * 100);
      if (sx) (mx += sx.by), guides.value.push({ axis: "x", at: sx.at });
      if (sy) (my += sy.by), guides.value.push({ axis: "y", at: sy.at });
    }
    for (const s of start.at) {
      s.b.x = round(s.x + mx);
      s.b.y = round(s.y + my);
    }
  });
}

function resize(event, one, at) {
  d.remember();
  const P = paper.value;
  const t = ((one.rotate || 0) * Math.PI) / 180;
  const cos = Math.cos(t);
  const sin = Math.sin(t);
  const w0 = (one.w / 100) * P.w;
  const h0 = (one.h / 100) * P.h;
  const cx0 = (one.x / 100) * P.w + w0 / 2;
  const cy0 = (one.y / 100) * P.h + h0 / 2;
  const sx = at.includes("e") ? 1 : at.includes("w") ? -1 : 0;
  const sy = at.includes("s") ? 1 : at.includes("n") ? -1 : 0;
  const start = { x: event.clientX, y: event.clientY };
  const targets = lines([one.id]);
  follow((e) => {
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    const lx = dx * cos + dy * sin;
    const ly = -dx * sin + dy * cos;
    let w = Math.max(4, w0 + sx * lx);
    let h = Math.max(4, h0 + sy * ly);
    if (e.shiftKey && sx && sy) {
      const ratio = w0 / h0;
      if (w / w0 > h / h0) h = w / ratio;
      else w = h * ratio;
    }
    const shx = (sx * (w - w0)) / 2;
    const shy = (sy * (h - h0)) / 2;
    const cx = cx0 + cos * shx - sin * shy;
    const cy = cy0 + sin * shx + cos * shy;
    let x = ((cx - w / 2) / P.w) * 100;
    let y = ((cy - h / 2) / P.h) * 100;
    let pw = (w / P.w) * 100;
    let ph = (h / P.h) * 100;
    guides.value = [];
    if (!one.rotate && !e.altKey) {
      const nx = (NEAR / P.w) * 100;
      const ny = (NEAR / P.h) * 100;
      const ex = sx > 0 ? settle([x + pw], targets.xs, nx) : sx < 0 ? settle([x], targets.xs, nx) : null;
      const ey = sy > 0 ? settle([y + ph], targets.ys, ny) : sy < 0 ? settle([y], targets.ys, ny) : null;
      if (ex) (sx > 0 ? (pw += ex.by) : ((x += ex.by), (pw -= ex.by))), guides.value.push({ axis: "x", at: ex.at });
      if (ey) (sy > 0 ? (ph += ey.by) : ((y += ey.by), (ph -= ey.by))), guides.value.push({ axis: "y", at: ey.at });
    }
    Object.assign(one, { x: round(x), y: round(y), w: round(Math.max(pw, 0.2)), h: round(Math.max(ph, 0.2)) });
  });
}

function turn(event, one) {
  d.remember();
  const paperRect = sheet.value.getBoundingClientRect();
  const cx = paperRect.left + ((one.x + one.w / 2) / 100) * paper.value.w;
  const cy = paperRect.top + ((one.y + one.h / 2) / 100) * paper.value.h;
  follow((e) => {
    let deg = (Math.atan2(e.clientY - cy, e.clientX - cx) * 180) / Math.PI + 90;
    if (e.shiftKey) deg = Math.round(deg / 15) * 15;
    else if (Math.abs(deg - Math.round(deg / 90) * 90) < 4) deg = Math.round(deg / 90) * 90;
    deg = ((((deg + 180) % 360) + 360) % 360) - 180;
    one.rotate = Math.round(deg);
  });
}

// Pressing on the empty canvas: a click chooses the slide itself, a drag
// draws a box and chooses every block it touches.
function sweep(event) {
  if (event.button !== 0 || !d.design.value) return;
  const rect = sheet.value.getBoundingClientRect();
  const adding = event.shiftKey || event.metaKey || event.ctrlKey;
  const at = (e) => ({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  const start = at(event);
  band.value = null;
  follow(
    (e) => {
      const now = at(e);
      if (!band.value && Math.hypot(now.x - start.x, now.y - start.y) < 3) return;
      band.value = { x0: start.x, y0: start.y, x1: now.x, y1: now.y };
    },
    () => {
      const b = band.value;
      band.value = null;
      if (!b) return adding || d.choose([]);
      const [l, r] = [Math.min(b.x0, b.x1), Math.max(b.x0, b.x1)].map((v) => (v / paper.value.w) * 100);
      const [t, u] = [Math.min(b.y0, b.y1), Math.max(b.y0, b.y1)].map((v) => (v / paper.value.h) * 100);
      const hit = shown.value.filter((one) => !one.locked && one.x < r && one.x + one.w > l && one.y < u && one.y + one.h > t).map((one) => one.id);
      d.choose(hit, adding);
    },
  );
}

async function edit(one) {
  if (one.kind !== "text" || one.locked || !d.writable.value) return;
  d.choose(one.id);
  d.s.editing = one.id;
  await nextTick();
  const el = editor.value;
  if (!el) return;
  el.innerText = one.text || "";
  el.focus();
  const range = document.createRange();
  range.selectNodeContents(el);
  const picked = document.getSelection();
  picked.removeAllRanges();
  picked.addRange(range);
}

function finish() {
  const one = editing.value;
  if (!one) return;
  const said = (editor.value?.innerText || "").replace(/\n$/, "");
  d.s.editing = null;
  d.set(one, "text", said);
}

let observer = null;
onMounted(() => {
  measure();
  observer = new ResizeObserver(measure);
  observer.observe(area.value);
});
onBeforeUnmount(() => observer?.disconnect());

defineExpose({ measure, edit });
</script>
