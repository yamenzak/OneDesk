<template>
  <div class="flex h-full min-h-0 flex-col" :class="card ? 'overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-elevation-2 p-1.5' : ''">
    <div v-if="card && selected.size" class="flex h-9 shrink-0 items-center gap-2 rounded-full bg-surface-gray-3 pe-1.5 ps-3 text-sm font-medium text-ink-gray-9">
      <Checkbox :model-value="every" :indeterminate="!every" :aria-label="every ? __('Clear selection') : __('Select all')" :title="every ? __('Clear selection') : __('Select all')" @update:model-value="(on) => emit('all', on)" />
      <span class="min-w-0 flex-1 truncate">{{ __("{0} selected", [selected.size]) }}</span>
      <span class="flex shrink-0 items-center gap-0.5"><slot name="action" /></span>
    </div>
    <div
      v-else-if="view === 'details'"
      class="grid shrink-0 items-center text-sm"
      :class="[grid, card ? 'h-9 rounded-full bg-surface-gray-3 px-2 font-medium text-ink-gray-7' : 'border-b border-outline-gray-1 px-2 py-1.5 text-ink-gray-5']"
    >
      <span v-for="col in columns" :key="col.key" class="flex min-w-0 items-center gap-2" :class="col.class">
        <Checkbox
          v-if="card && col.key === 'name'"
          :model-value="false"
          :disabled="!items.length"
          :aria-label="__('Select all')"
          :title="__('Select all')"
          class="ms-1"
          @update:model-value="(on) => emit('all', on)"
        />
        <button type="button" class="flex min-w-0 flex-1 items-center gap-1 truncate rounded-2 px-1 text-start hover:text-ink-gray-8" :class="{ 'justify-end': col.key === 'size' }" @click="emit('sort', col.key)">
          {{ col.label }}
          <span v-if="sort.key === col.key" :class="sort.asc ? 'lucide-chevron-up' : 'lucide-chevron-down'" class="size-3" aria-hidden="true" />
        </button>
      </span>
    </div>
    <div v-if="scoped" class="flex shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-gray-1 px-3 py-1.5 text-sm text-ink-gray-6">
      <span :class="everywhere ? 'lucide-globe' : 'lucide-folder-search'" class="size-4" aria-hidden="true" />
      <span class="flex-1">{{ everywhere ? __("Results from everywhere") : __("Results in {0}", [hereName]) }}</span>
      <Button size="sm" variant="ghost" :label="everywhere ? __('Only in {0}', [hereName]) : __('Search everywhere')" @click="emit('everywhere')" />
    </div>
    <div
      ref="list"
      tabindex="0"
      role="listbox"
      aria-multiselectable="true"
      class="relative min-h-0 flex-1 overflow-auto outline-none"
      :class="[view === 'tiles' ? 'grid content-start gap-2 p-3 [grid-template-columns:repeat(auto-fill,minmax(7.5rem,1fr))]' : '', dropOn === here ? 'ring-2 ring-inset ring-outline-blue-5' : '']"
      @mousedown.self="emit('space', $event), lassoStart($event)"
      @contextmenu.self="emit('menu', $event, null)"
      @dragover="emit('dragover', $event, null)"
      @dragleave="emit('dragleave', $event, null)"
      @drop="emit('drop', $event, null)"
    >
      <div v-if="!items.length" class="py-16 text-center text-base text-ink-gray-5">{{ empty }}</div>
      <div
        v-if="box"
        class="pointer-events-none absolute z-10 rounded-2 border border-outline-gray-4 bg-surface-gray-3 opacity-60"
        :style="{ left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px`, height: `${box.height}px` }"
      />
      <div
        v-for="item in items"
        :key="item.id"
        role="option"
        draggable="true"
        :data-id="item.id"
        :aria-selected="selected.has(item.id)"
        class="group relative cursor-default select-none"
        :class="[
          view === 'details'
            ? ['grid items-center px-2 text-base', grid, card ? 'rounded-4 border-b border-outline-gray-1 py-2.5 last:border-b-0' : 'py-1.5']
            : 'flex flex-col items-center gap-1.5 rounded-4 p-2 text-center text-sm',
          selected.has(item.id) ? 'bg-surface-gray-4' : 'hover:bg-surface-gray-2',
          item.id === focusId ? 'ring-2 ring-inset ring-outline-gray-3' : '',
          cut.has(item.id) ? 'opacity-50' : '',
          dropOn === item.id ? 'ring-2 ring-inset ring-outline-blue-5' : '',
        ]"
        @mousedown="emit('pick', item.id, $event)"
        @dblclick="emit('open', item.id)"
        @contextmenu="emit('menu', $event, item.id)"
        @dragstart="emit('dragstart', $event, item.id)"
        @dragend="emit('dragend')"
        @dragover="item.folder && emit('dragover', $event, item.id)"
        @dragleave="item.folder && emit('dragleave', $event, item.id)"
        @drop="item.folder && emit('drop', $event, item.id)"
      >
        <span
          v-if="card && view === 'tiles'"
          class="absolute start-2 top-2 flex"
          :class="selected.has(item.id) ? '' : 'opacity-0 group-hover:opacity-100 max-md:opacity-100'"
          @mousedown.stop
          @dblclick.stop
        >
          <Checkbox :model-value="selected.has(item.id)" :aria-label="__('Select {0}', [item.name])" @update:model-value="emit('toggle', item.id)" />
        </span>
        <span class="flex min-w-0 items-center gap-2" :class="{ 'w-full flex-col': view === 'tiles' }">
          <span v-if="card && view === 'details'" class="ms-1 flex shrink-0" @mousedown.stop @dblclick.stop>
            <Checkbox :model-value="selected.has(item.id)" :aria-label="__('Select {0}', [item.name])" @update:model-value="emit('toggle', item.id)" />
          </span>
          <span class="flex shrink-0 items-center justify-center" :class="view === 'tiles' ? 'size-16' : 'size-5'">
            <img v-if="picture(item)" :src="picture(item)" alt="" loading="lazy" class="max-h-full max-w-full rounded-2 object-cover" />
            <span v-else :class="[iconOf(item), inkOf(item), view === 'tiles' ? 'size-10' : 'size-4']" aria-hidden="true" />
          </span>
          <input
            v-if="renaming === item.id"
            ref="renameBox"
            class="min-w-0 flex-1 rounded-2 border border-outline-gray-3 bg-surface-base px-1 py-0.5 text-base"
            :value="item.name"
            spellcheck="false"
            @keydown.stop="renameKey($event, item)"
            @blur="emit('renamed', item, $event.target.value)"
            @mousedown.stop
            @dblclick.stop
          />
          <span v-else class="flex min-w-0 flex-col" :class="{ 'w-full items-center': view === 'tiles' }">
            <span class="flex min-w-0 items-center gap-1" :class="{ 'max-w-full': view === 'tiles' }">
              <span class="truncate text-ink-gray-8">{{ item.name }}</span>
              <span v-if="item.count" class="shrink-0 text-sm text-ink-gray-5">{{ count(item.count) }}</span>
              <img v-if="item.intake && intakeOn" :src="oneaiMark" :alt="readNote" :title="readNote" class="size-3.5 shrink-0" />
              <span v-if="item.starred" class="lucide-star size-3 shrink-0 text-ink-amber-6" :title="__('Starred')" />
              <span v-if="item.shared" class="lucide-users size-3 shrink-0 text-ink-gray-5" :title="__('Shared')" />
              <span v-if="item.private === false && !item.folder" class="lucide-globe size-3 shrink-0 text-ink-gray-5" :title="publicNote" />
            </span>
            <span v-if="item.found" class="truncate text-sm text-ink-gray-5">{{ item.found }}</span>
            <span v-if="item.oneos" class="flex min-w-0 items-center gap-1 text-sm text-ink-blue-7">
              <span class="lucide-monitor size-3 shrink-0" aria-hidden="true" />
              <span class="truncate">{{ item.oneos.mine ? __("You are editing in OneOS") : __("{0} is editing in OneOS", [item.oneos.by]) }}</span>
            </span>
            <span v-else-if="item.editing" class="flex min-w-0 items-center gap-1 text-sm text-ink-blue-7">
              <span class="lucide-pencil size-3 shrink-0" aria-hidden="true" />
              <span class="truncate">{{ editingText(item.editing) }}</span>
            </span>
          </span>
        </span>
        <template v-if="view === 'details'">
          <span v-if="showWhere" class="truncate text-sm text-ink-gray-6">{{ item.where || "" }}</span>
          <span class="truncate text-sm text-ink-gray-6 max-md:hidden">{{ dateText(kind === "bin" ? item.deleted : item.modified) }}</span>
          <span class="truncate text-sm text-ink-gray-6 max-lg:hidden">{{ typeOf(item) }}</span>
          <span class="truncate text-end text-sm text-ink-gray-6 max-md:hidden">{{ item.folder ? "" : sizeText(item.size) }}</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
// The files and folders here, as Explorer draws them: Details, a row each
// with its folder, date, type and size, sortable by any of them; or Tiles,
// a picture each.
import { computed, nextTick, ref, watch } from "vue";
import { Button, Checkbox } from "frappe-ui";

import { __, andList, count, oneaiMark, name as appName } from "../kit";
import { PREVIEW, dateText, extension, iconOf, inkOf, sizeText, typeOf } from "./cloud";

const props = defineProps({
  items: { type: Array, default: () => [] },
  view: { type: String, default: "details" },
  sort: { type: Object, required: true },
  selected: { type: Set, required: true },
  cut: { type: Set, required: true },
  focusId: { type: String, default: null },
  renaming: { type: String, default: null },
  kind: { type: String, default: "folder" },
  whereHead: { type: String, default: "" },
  empty: { type: String, default: "" },
  scoped: Boolean,
  searching: Boolean,
  everywhere: Boolean,
  hereName: { type: String, default: "" },
  here: { type: String, default: "" },
  dropOn: { type: String, default: null },
  intakeOn: Boolean,
  card: Boolean,
});
const emit = defineEmits(["pick", "open", "sort", "space", "menu", "renamed", "everywhere", "dragstart", "dragend", "dragover", "dragleave", "drop", "toggle", "all", "lasso"]);

// The Folder column is there only where it says something: in search results
// and the places that list from elsewhere (shared, recent, starred, libraries).
const WITH_WHERE =
  "grid-cols-[minmax(0,1fr)_9rem_9.5rem_7rem_4.5rem] max-lg:grid-cols-[minmax(0,1fr)_9rem_9.5rem_4.5rem] max-md:grid-cols-[minmax(0,1fr)_8rem] gap-2";
const WITHOUT_WHERE = "grid-cols-[minmax(0,1fr)_9.5rem_7rem_4.5rem] max-lg:grid-cols-[minmax(0,1fr)_9.5rem_4.5rem] max-md:grid-cols-[minmax(0,1fr)] gap-2";
const readNote = __("Read by {0}", [appName("one_ai")]);

function editingText({ by, mine, app }) {
  if (!by.length) return __("You are editing in {0}", [app]);
  const names = mine ? [__("You"), ...by] : by;
  return names.length === 1 ? __("{0} is editing in {1}", [names[0], app]) : __("{0} are editing in {1}", [andList(names), app]);
}
const publicNote = __("Anyone with the link can open this file");

const showWhere = computed(() => !!props.whereHead || props.scoped || props.searching);
const grid = computed(() => (showWhere.value ? WITH_WHERE : WITHOUT_WHERE));

const columns = computed(() => [
  { key: "name", label: __("Name") },
  showWhere.value ? { key: "where", label: props.whereHead || __("Folder") } : null,
  { key: "modified", label: props.kind === "bin" ? __("Date deleted") : __("Date modified"), class: "max-md:hidden" },
  { key: "type", label: __("Type"), class: "max-lg:hidden" },
  { key: "size", label: __("Size"), class: "justify-end max-md:hidden" },
].filter(Boolean));

const picture = (item) =>
  item.thumbnail || (!item.folder && PREVIEW.image.includes(extension(item)) && item.url && !item.url.startsWith("/api/") ? item.url : null);

const list = ref(null);
const renameBox = ref(null);

watch(
  () => props.renaming,
  async (id) => {
    if (!id) return;
    await nextTick();
    const box = [renameBox.value].flat()[0];
    const item = props.items.find((one) => one.id === id);
    if (!box || !item) return;
    box.focus();
    const dot = item.folder ? -1 : item.name.lastIndexOf(".");
    box.setSelectionRange(0, dot > 0 ? dot : item.name.length);
  }
);

function renameKey(event, item) {
  if (event.key === "Enter") event.target.blur();
  if (event.key === "Escape") emit("renamed", item, null);
}

function columnsAcross() {
  const tiles = [...(list.value?.querySelectorAll("[data-id]") || [])];
  if (!tiles.length) return 1;
  const top = tiles[0].offsetTop;
  return Math.max(1, tiles.filter((el) => el.offsetTop === top).length);
}

function reveal(id) {
  const el = list.value?.querySelector(`[data-id="${CSS.escape(id)}"]`);
  el?.scrollIntoView({ block: "nearest" });
}

const focus = () => list.value?.focus();

const every = computed(() => props.items.length > 0 && props.items.every((one) => props.selected.has(one.id)));

// Dragging from an empty part of the list draws a box, and what it crosses is
// chosen, added to what was chosen when Ctrl, Cmd or Shift is held, as
// Explorer and Finder do.
const box = ref(null);
let from = null;

function lassoStart(event) {
  if (!props.card || event.button !== 0) return;
  const el = list.value;
  const at = el.getBoundingClientRect();
  from = { x: event.clientX - at.left + el.scrollLeft, y: event.clientY - at.top + el.scrollTop, add: event.ctrlKey || event.metaKey || event.shiftKey, begun: false };
  document.addEventListener("mousemove", lassoMove);
  document.addEventListener("mouseup", lassoEnd, { once: true });
}

function lassoMove(event) {
  const el = list.value;
  if (!from || !el) return;
  const at = el.getBoundingClientRect();
  const x = event.clientX - at.left + el.scrollLeft;
  const y = event.clientY - at.top + el.scrollTop;
  if (!from.begun && Math.abs(x - from.x) + Math.abs(y - from.y) < 6) return;
  event.preventDefault();
  box.value = { left: Math.min(x, from.x), top: Math.min(y, from.y), width: Math.abs(x - from.x), height: Math.abs(y - from.y) };
  const left = at.left - el.scrollLeft + box.value.left;
  const top = at.top - el.scrollTop + box.value.top;
  const right = left + box.value.width;
  const bottom = top + box.value.height;
  const crossed = [...el.querySelectorAll("[data-id]")]
    .filter((row) => {
      const r = row.getBoundingClientRect();
      return r.left < right && r.right > left && r.top < bottom && r.bottom > top;
    })
    .map((row) => row.dataset.id);
  emit("lasso", crossed, from.add, !from.begun);
  from.begun = true;
}

function lassoEnd() {
  document.removeEventListener("mousemove", lassoMove);
  from = null;
  box.value = null;
}

defineExpose({ columnsAcross, reveal, focus });
</script>
