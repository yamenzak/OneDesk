// The designer's state, shared by its parts (provide/inject): the playlist's
// slides, the one being drawn, which blocks are chosen, and the history that
// Undo walks back through. What a block may hold is the server's schema
// (one_display/blocks.py), handed over with the slides.
import { computed, inject, provide, reactive } from "vue";

const KEY = Symbol("designer");
const HISTORY = 100;
let seq = 0;

export const newId = (prefix = "b") => `${prefix}${Date.now().toString(36)}${(++seq).toString(36)}`;
export const clamp = (v, low, high) => Math.min(Math.max(v, low), high);
export const round = (v) => Math.round(v * 100) / 100;

export function makeDesigner() {
  const s = reactive({
    said: null,
    schema: null,
    slides: [],
    picked: null,
    chosen: [],
    editing: null,
    dirty: false,
    zoom: "fit",
    qrs: {},
    clipboard: null,
    past: [],
    future: [],
    held: {},
  });

  const slide = computed(() => s.slides.find((one) => one.key === s.picked) || null);
  const design = computed(() => (slide.value?.kind === "Design" ? slide.value.design : null));
  const blocks = computed(() => design.value?.blocks || []);
  const chosenBlocks = computed(() => blocks.value.filter((one) => s.chosen.includes(one.id)));
  const only = computed(() => (chosenBlocks.value.length === 1 ? chosenBlocks.value[0] : null));
  const writable = computed(() => Boolean(s.said?.writable));
  const portrait = computed(() => design.value?.orientation === "Portrait");
  const size = computed(() => (portrait.value ? { w: 1080, h: 1920 } : { w: 1920, h: 1080 }));

  const snapshot = () => JSON.stringify({ slides: s.slides, picked: s.picked });

  // Kept before a change, so Undo returns to it. A run of the same change
  // (typing in one field, one drag) is one step, not one per keystroke.
  function remember(run = null) {
    const now = Date.now();
    if (run && s.held.run === run && now - s.held.at < 800) {
      s.held.at = now;
      return;
    }
    s.held = { run, at: now };
    s.past.push(snapshot());
    if (s.past.length > HISTORY) s.past.shift();
    s.future = [];
    s.dirty = true;
  }

  function restore(from, to) {
    if (!from.length) return;
    to.push(snapshot());
    const back = JSON.parse(from.pop());
    s.slides = back.slides;
    s.picked = back.picked;
    s.chosen = s.chosen.filter((id) => blocks.value.some((one) => one.id === id));
    s.editing = null;
    s.held = {};
    s.dirty = true;
  }

  const undo = () => restore(s.past, s.future);
  const redo = () => restore(s.future, s.past);

  function choose(ids, adding = false) {
    const list = Array.isArray(ids) ? ids : [ids];
    if (!adding) s.chosen = list;
    else if (list.length === 1) s.chosen = s.chosen.includes(list[0]) ? s.chosen.filter((id) => id !== list[0]) : [...s.chosen, list[0]];
    else s.chosen = [...new Set([...s.chosen, ...list])];
    if (s.editing && !s.chosen.includes(s.editing)) s.editing = null;
  }

  function set(target, name, value, run) {
    if (target[name] === value) return;
    remember(run || `${target.id || "slide"}:${name}`);
    target[name] = value;
  }

  function blank() {
    return { ...s.schema.slide_defaults, blocks: [] };
  }

  function add(kind, extra = {}) {
    const spec = s.schema.kinds[kind];
    const [w, h] = spec.size;
    const { w: W, h: H } = size.value;
    const tall = portrait.value ? (h * H) / W / 1.8 : h;
    const one = { ...spec.defaults, id: newId(), kind, x: round((100 - w) / 2), y: round((100 - tall) / 2), w, h: round(tall), ...extra };
    remember();
    design.value.blocks.push(one);
    choose(one.id);
    return one;
  }

  function remove() {
    if (!s.chosen.length) return;
    remember();
    design.value.blocks = blocks.value.filter((one) => !s.chosen.includes(one.id) || one.locked);
    s.chosen = s.chosen.filter((id) => blocks.value.some((one) => one.id === id));
  }

  function copies(list, by = 2) {
    return list.map((one) => ({ ...JSON.parse(JSON.stringify(one)), id: newId(), x: round(one.x + by), y: round(one.y + by), locked: 0 }));
  }

  function duplicate() {
    if (!chosenBlocks.value.length) return;
    remember();
    const made = copies(chosenBlocks.value);
    design.value.blocks.push(...made);
    choose(made.map((one) => one.id));
  }

  const copy = () => (s.clipboard = chosenBlocks.value.length ? JSON.parse(JSON.stringify(chosenBlocks.value)) : s.clipboard);

  function paste() {
    if (!s.clipboard?.length || !design.value) return;
    remember();
    const made = copies(s.clipboard);
    design.value.blocks.push(...made);
    choose(made.map((one) => one.id));
  }

  // Order is drawing order: the last block is on top.
  function restack(how) {
    if (!chosenBlocks.value.length) return;
    remember();
    const list = [...blocks.value];
    const chosen = list.filter((one) => s.chosen.includes(one.id));
    const rest = list.filter((one) => !s.chosen.includes(one.id));
    if (how === "front") return (design.value.blocks = [...rest, ...chosen]);
    if (how === "back") return (design.value.blocks = [...chosen, ...rest]);
    const step = how === "forward" ? 1 : -1;
    const order = step > 0 ? [...list.keys()].reverse() : [...list.keys()];
    for (const at of order) {
      const to = at + step;
      if (!s.chosen.includes(list[at].id) || to < 0 || to >= list.length || s.chosen.includes(list[to].id)) continue;
      [list[at], list[to]] = [list[to], list[at]];
    }
    design.value.blocks = list;
  }

  function moveLayer(id, before) {
    const list = [...blocks.value];
    const from = list.findIndex((one) => one.id === id);
    if (from < 0) return;
    remember();
    const [one] = list.splice(from, 1);
    const to = before == null ? list.length : list.findIndex((other) => other.id === before);
    list.splice(to < 0 ? list.length : to, 0, one);
    design.value.blocks = list;
  }

  // Lines up the chosen blocks with each other, or one block with the slide.
  function align(how) {
    const list = chosenBlocks.value.filter((one) => !one.locked);
    if (!list.length) return;
    remember();
    const alone = list.length === 1;
    const left = alone ? 0 : Math.min(...list.map((one) => one.x));
    const top = alone ? 0 : Math.min(...list.map((one) => one.y));
    const right = alone ? 100 : Math.max(...list.map((one) => one.x + one.w));
    const bottom = alone ? 100 : Math.max(...list.map((one) => one.y + one.h));
    for (const one of list) {
      if (how === "left") one.x = round(left);
      if (how === "centre") one.x = round((left + right) / 2 - one.w / 2);
      if (how === "right") one.x = round(right - one.w);
      if (how === "top") one.y = round(top);
      if (how === "middle") one.y = round((top + bottom) / 2 - one.h / 2);
      if (how === "bottom") one.y = round(bottom - one.h);
    }
  }

  function distribute(axis) {
    const list = [...chosenBlocks.value].filter((one) => !one.locked);
    if (list.length < 3) return;
    remember();
    const [pos, len] = axis === "across" ? ["x", "w"] : ["y", "h"];
    list.sort((a, b) => a[pos] - b[pos]);
    const start = list[0][pos];
    const end = list[list.length - 1][pos] + list[list.length - 1][len];
    const room = end - start - list.reduce((sum, one) => sum + one[len], 0);
    const gap = room / (list.length - 1);
    let at = start;
    for (const one of list) {
      one[pos] = round(at);
      at += one[len] + gap;
    }
  }

  const store = {
    s,
    slide,
    design,
    blocks,
    chosenBlocks,
    only,
    writable,
    portrait,
    size,
    remember,
    undo,
    redo,
    choose,
    set,
    blank,
    add,
    remove,
    duplicate,
    copy,
    paste,
    restack,
    moveLayer,
    align,
    distribute,
  };
  provide(KEY, store);
  return store;
}

export const useDesigner = () => inject(KEY);
