<template>
  <div class="flex h-full min-h-0 w-full">
    <aside class="w-56 shrink-0 overflow-y-auto border-e border-outline-gray-1 p-3">
      <h3 class="mb-2 text-sm font-medium text-ink-gray-5">{{ __("Add a Widget") }}</h3>
      <button
        v-for="one in said?.types || []"
        :key="one.type"
        class="mb-1 block w-full rounded-2 px-2 py-1.5 text-start hover:bg-surface-gray-2 disabled:opacity-50"
        :disabled="!said.writable"
        :title="one.about"
        @click="add(one)"
      >
        <span class="block text-base text-ink-gray-8">{{ one.label }}</span>
        <span class="block truncate text-sm text-ink-gray-5">{{ one.about }}</span>
      </button>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col">
      <div class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-2">
        <span class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-8">{{ said?.name }}</span>
        <div v-if="said" class="w-36 shrink-0">
          <FormControl v-model="orientation" type="select" :options="orientations" @update:model-value="dirty = true" />
        </div>
        <Button :label="__('Preview')" icon-left="lucide-monitor-play" @click="preview" />
        <Button variant="solid" :label="__('Save')" :loading="saving" :disabled="!dirty || !said?.writable" @click="save" />
      </div>
      <div ref="area" class="flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-surface-gray-2 p-6">
        <Loading v-if="!said" />
        <div
          v-else
          ref="stage"
          class="relative overflow-hidden rounded-2 bg-surface-gray-7"
          :style="{ width: `${frame.w}px`, height: `${frame.h}px` }"
          @pointerdown.self="selected = null"
        >
          <iframe :key="shown" class="pointer-events-none absolute inset-0 h-full w-full border-0" :src="iframeSrc" />
          <div
            v-for="one in placed"
            :key="one.key"
            class="absolute cursor-move select-none rounded-1 border border-dashed"
            :class="one.key === selected ? 'border-outline-gray-5' : 'border-outline-gray-3 hover:border-outline-gray-4'"
            :style="box(one)"
            @pointerdown.stop="grab($event, one, 'move')"
          >
            <span class="absolute start-0 top-0 rounded-br bg-surface-gray-7 px-1.5 py-0.5 text-xs text-ink-white">
              {{ one.label || typeOf(one)?.label }}
            </span>
            <span
              v-if="one.key === selected"
              class="absolute bottom-0 end-0 h-3 w-3 cursor-se-resize rounded-1 bg-surface-gray-7"
              @pointerdown.stop="grab($event, one, 'size')"
            />
          </div>
        </div>
      </div>
    </main>

    <aside class="w-80 shrink-0 overflow-y-auto border-s border-outline-gray-1 p-4">
      <p v-if="!current" class="text-sm text-ink-gray-5">{{ __("Choose a widget on the screen, or add one.") }}</p>
      <div v-else class="flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <span class="me-auto text-base font-medium text-ink-gray-8">{{ typeOf(current)?.label }}</span>
          <Button variant="ghost" icon="lucide-trash-2" :aria-label="__('Remove')" :title="__('Remove')" @click="remove" />
        </div>
        <FormControl v-model="current.label" :label="__('Label')" type="text" @update:model-value="dirty = true" />
        <div class="grid grid-cols-4 gap-2">
          <FormControl v-for="key in ['x', 'y', 'w', 'h']" :key="key" v-model.number="current[key]" :label="edges[key]" type="number" @update:model-value="dirty = true" />
        </div>

        <template v-if="typeOf(current)?.sources.length">
          <FormControl v-model="current.source" :label="__('Source')" type="select" :options="sourceOptions" @update:model-value="sourceChanged" />
          <a class="text-sm text-ink-gray-5 underline" href="/desk/display-source/new" target="_blank">{{ __("New Source") }}</a>
        </template>

        <template v-if="current.source && typeOf(current)?.slots.length">
          <h4 class="mt-1 text-sm font-medium text-ink-gray-5">{{ __("Fields Shown") }}</h4>
          <div v-for="slot in typeOf(current).slots" :key="slot" class="flex flex-col gap-1">
            <FormControl
              :model-value="current.mapping[slot] || ''"
              :label="slots[slot] || slot"
              type="text"
              :placeholder="__('Such as {0}', ['{title}'])"
              @update:model-value="(v) => setSlot(slot, v)"
            />
            <FormControl v-if="fields.length" :model-value="''" type="select" :options="fieldOptions" @update:model-value="(v) => v && setSlot(slot, `${current.mapping[slot] || ''}{${v}}`)" />
          </div>
          <div v-if="peeked.length" class="rounded-2 border border-outline-gray-1 p-2">
            <p class="mb-1 text-xs text-ink-gray-5">{{ __("Shows now") }}</p>
            <p v-for="(row, i) in peeked" :key="i" class="truncate text-sm text-ink-gray-7">{{ Object.values(row).filter(Boolean).join(" · ") }}</p>
          </div>
        </template>

        <h4 v-if="typeOf(current)?.settings.length" class="mt-1 text-sm font-medium text-ink-gray-5">{{ __("Settings") }}</h4>
        <template v-for="field in typeOf(current)?.settings || []" :key="field.key">
          <FormControl
            v-if="field.kind === 'check'"
            :model-value="Boolean(setting(field))"
            :label="field.label"
            type="checkbox"
            @update:model-value="(v) => set(field.key, v ? 1 : 0)"
          />
          <FormControl
            v-else-if="field.kind === 'select'"
            :model-value="setting(field)"
            :label="field.label"
            type="select"
            :options="field.options"
            @update:model-value="(v) => set(field.key, v)"
          />
          <div v-else-if="field.kind === 'long' || field.kind === 'code'" class="flex flex-col gap-1">
            <FormControl
              :model-value="setting(field)"
              :label="field.label"
              type="textarea"
              :rows="field.kind === 'code' ? 10 : 3"
              :class="field.kind === 'code' ? 'font-mono' : ''"
              @update:model-value="(v) => set(field.key, v)"
            />
            <Button v-if="field.kind === 'code' && oneaiOn()" :label="__('Write with OneAI')" icon-left="lucide-sparkles" :loading="writing" @click="write(field.key)" />
          </div>
          <div v-else-if="field.kind === 'image'" class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ field.label }}</span>
            <img v-if="setting(field)" :src="setting(field)" class="max-h-24 self-start rounded-2" />
            <Button :label="__('Upload')" icon-left="lucide-upload" @click="uploadTo(field.key)" />
          </div>
          <FormControl
            v-else
            :model-value="setting(field)"
            :label="field.label"
            :type="field.kind === 'number' ? 'number' : 'text'"
            :placeholder="field.kind === 'colour' ? __('Brand colour') : ''"
            @update:model-value="(v) => set(field.key, field.kind === 'number' ? Number(v) : v)"
          />
        </template>

        <FormControl v-model="current.shown" :label="__('Shown')" type="select" :options="shownOptions" @update:model-value="dirty = true" />
        <div v-if="current.shown === 'Between Times'" class="grid grid-cols-2 gap-2">
          <FormControl v-model="current.from_time" :label="__('From')" type="time" @update:model-value="dirty = true" />
          <FormControl v-model="current.to_time" :label="__('To')" type="time" @update:model-value="dirty = true" />
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, FormControl } from "frappe-ui";

import { Loading, __, call, oneaiOn, openTab, prompt, upload } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
});

const API = "onedesk.one_display.layout.";
const said = ref(null);
const placed = ref([]);
const orientation = ref("Landscape");
const selected = ref(null);
const dirty = ref(false);
const saving = ref(false);
const shown = ref(0);
const fields = ref([]);
const peeked = ref([]);
const area = ref(null);
const stage = ref(null);
const room = ref({ w: 960, h: 540 });
let seq = 0;

const name = computed(() => props.route[0] || props.query.collection || "");
const orientations = [
  { label: __("Landscape"), value: "Landscape" },
  { label: __("Portrait"), value: "Portrait" },
];
const shownOptions = [
  { label: __("Always"), value: "Always" },
  { label: __("Between Times"), value: "Between Times" },
];
const edges = { x: __("Left"), y: __("Top"), w: __("Width"), h: __("Height") };
const slots = { text: __("Words"), title: __("Line"), subtitle: __("Smaller Line"), value: __("Figure"), image: __("Picture"), label: __("Label"), link: __("Address") };

const frame = computed(() => {
  const ratio = orientation.value === "Portrait" ? 9 / 16 : 16 / 9;
  const w = Math.min(room.value.w, room.value.h * ratio);
  return { w, h: w / ratio };
});
const iframeSrc = computed(() => `/tv?collection=${encodeURIComponent(name.value)}&embed=1`);
const current = computed(() => placed.value.find((one) => one.key === selected.value) || null);
const typeOf = (one) => said.value?.types.find((t) => t.type === one.widget_type);
const sourceOptions = computed(() => {
  const kinds = typeOf(current.value)?.sources || [];
  return [{ label: "", value: "" }, ...said.value.sources.filter((s) => kinds.includes(s.kind)).map((s) => ({ label: `${s.name} · ${__(s.kind)}`, value: s.name }))];
});
const fieldOptions = computed(() => [{ label: __("Insert a field"), value: "" }, ...fields.value.map((f) => ({ label: f.label || f.fieldname, value: f.fieldname }))]);

function parse(text) {
  if (text && typeof text === "object") return text;
  try {
    return JSON.parse(text || "{}") || {};
  } catch {
    return {};
  }
}

function adopt(data) {
  said.value = data;
  orientation.value = data.orientation;
  placed.value = data.widgets.map((one) => ({ ...one, key: one.id, mapping: parse(one.mapping), settings: parse(one.settings) }));
  dirty.value = false;
}

async function load() {
  adopt(await call(API + "get", { collection: name.value }));
}

function measure() {
  if (!area.value) return;
  const rect = area.value.getBoundingClientRect();
  room.value = { w: Math.max(rect.width - 48, 200), h: Math.max(rect.height - 48, 120) };
}

const box = (one) => ({ left: `${one.x}%`, top: `${one.y}%`, width: `${one.w}%`, height: `${one.h}%`, zIndex: one.layer || 1 });

function add(type) {
  const [w, h] = type.size;
  const one = {
    key: `new-${++seq}`,
    id: null,
    widget_type: type.type,
    label: "",
    source: "",
    x: Math.max(0, (100 - w) / 2),
    y: Math.max(0, (100 - h) / 2),
    w,
    h,
    layer: placed.value.length + 1,
    mapping: {},
    settings: {},
    shown: "Always",
  };
  placed.value.push(one);
  selected.value = one.key;
  dirty.value = true;
}

function remove() {
  placed.value = placed.value.filter((one) => one.key !== selected.value);
  selected.value = null;
  dirty.value = true;
}

const clamp = (v, low, high) => Math.min(Math.max(v, low), high);
const snap = (v) => Math.round(v * 2) / 2;

function grab(event, one, how) {
  if (!said.value.writable) return;
  selected.value = one.key;
  const rect = stage.value.getBoundingClientRect();
  const start = { x: event.clientX, y: event.clientY, one: { ...one } };
  const move = (e) => {
    const dx = ((e.clientX - start.x) / rect.width) * 100;
    const dy = ((e.clientY - start.y) / rect.height) * 100;
    if (how === "move") {
      one.x = snap(clamp(start.one.x + dx, 0, 100 - one.w));
      one.y = snap(clamp(start.one.y + dy, 0, 100 - one.h));
    } else {
      one.w = snap(clamp(start.one.w + dx, 2, 100 - one.x));
      one.h = snap(clamp(start.one.h + dy, 2, 100 - one.y));
    }
    dirty.value = true;
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
  const step = event.shiftKey ? 5 : 0.5;
  const moves = { ArrowLeft: ["x", -step], ArrowRight: ["x", step], ArrowUp: ["y", -step], ArrowDown: ["y", step] };
  if (event.key === "Delete" || event.key === "Backspace") return remove();
  const move = moves[event.key];
  if (!move) return;
  event.preventDefault();
  const [key, by] = move;
  const limit = key === "x" ? 100 - current.value.w : 100 - current.value.h;
  current.value[key] = clamp(current.value[key] + by, 0, limit);
  dirty.value = true;
}

const setting = (field) => (field.key in current.value.settings ? current.value.settings[field.key] : field.default);

function set(key, value) {
  current.value.settings = { ...current.value.settings, [key]: value };
  dirty.value = true;
}

function setSlot(slot, value) {
  current.value.mapping = { ...current.value.mapping, [slot]: value };
  dirty.value = true;
  peek();
}

function uploadTo(key) {
  upload(null, null, (file) => set(key, file.file_url), { allow_multiple: false, make_attachments_public: true, restrictions: { allowed_file_types: ["image/*"] } });
}

async function sourceChanged() {
  dirty.value = true;
  await loadFields();
}

async function loadFields() {
  fields.value = [];
  peeked.value = [];
  if (!current.value?.source) return;
  fields.value = await call(API + "fields", { source: current.value.source });
  peek();
}

let peeking = null;
function peek() {
  clearTimeout(peeking);
  peeking = setTimeout(async () => {
    if (!current.value?.source) return;
    const data = await call("onedesk.one_display.sources.peek", {
      source: current.value.source,
      mapping: JSON.stringify(current.value.mapping || {}),
      widget_type: current.value.widget_type,
    });
    peeked.value = (data.rows || []).slice(0, 3);
  }, 400);
}

const writing = ref(false);

function write(key) {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows and does"), reqd: 1 }],
    async ({ description }) => {
      writing.value = true;
      try {
        const code = await call("onedesk.one_display.make.widget", {
          description,
          rows: peeked.value.length ? JSON.stringify(peeked.value) : null,
        });
        set(key, code);
      } finally {
        writing.value = false;
      }
    },
    __("Write a Widget"),
    __("Write"),
  );
}

async function save() {
  saving.value = true;
  try {
    const widgets = placed.value.map(({ key, ...one }) => one);
    adopt(await call(API + "save", { collection: name.value, widgets: JSON.stringify(widgets), orientation: orientation.value }));
    selected.value = null;
    shown.value += 1;
  } finally {
    saving.value = false;
  }
}

function preview() {
  openTab(iframeSrc.value.replace("&embed=1", ""));
}

watch(selected, loadFields);

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
