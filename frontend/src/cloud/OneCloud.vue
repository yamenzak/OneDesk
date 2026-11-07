<template>
  <InterfacePart v-if="win && !chosen.length && commands.some((one) => !one.off)" :win="win" part="commands" inline>
    <span class="inline-flex items-center gap-0.5">
      <template v-for="one in commands.filter((c) => !c.off)" :key="one.act">
        <Button v-if="one.label" variant="ghost" :icon-left="one.icon" :label="one.label" @click="act(one.act)" />
        <Button v-else variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" @click="act(one.act)" />
      </template>
    </span>
  </InterfacePart>
  <InterfacePart v-if="win" :win="win" part="details" details-key="onecloud">
    <div class="rounded-6 border border-outline-gray-2">
      <CloudPreview :chosen="chosen" :items="items" :node="node" :here-name="here?.name || ''" @changed="refresh" />
    </div>
  </InterfacePart>

  <div ref="root" class="relative flex h-full min-h-0 flex-col text-ink-gray-8 outline-none" tabindex="-1" @keydown="key">
    <template v-if="!win">
      <div class="flex items-center gap-0.5 border-b border-outline-gray-1 px-2 py-1">
        <Button variant="ghost" icon="lucide-arrow-left" :aria-label="__('Back')" :title="__('Back')" :disabled="!past.length" @click="act('back')" />
        <Button variant="ghost" icon="lucide-arrow-right" :aria-label="__('Forward')" :title="__('Forward')" :disabled="!ahead.length" @click="act('forward')" />
        <Button v-if="!room || node !== room" variant="ghost" icon="lucide-arrow-up" :aria-label="__('Up')" :title="__('Up')" :disabled="trail.length < 2" @click="act('up')" />
        <nav class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden px-2 text-base" :aria-label="__('Path')">
          <template v-for="(one, at) in crumbs" :key="one.id">
            <span v-if="at" class="text-ink-gray-4">/</span>
            <button v-if="at < crumbs.length - 1" type="button" class="truncate text-ink-gray-6 hover:text-ink-gray-9" @click="go(one.id)">{{ one.name }}</button>
            <span v-else class="truncate font-medium text-ink-gray-9">{{ one.name }}</span>
          </template>
        </nav>
        <Button variant="ghost" icon="lucide-refresh-cw" :aria-label="__('Refresh')" :title="__('Refresh')" @click="act('refresh')" />
        <TextInput ref="searchInput" v-model="typed" class="w-56" type="search" :placeholder="searchPlaceholder" @keydown="searchKey">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <template v-if="picker">
          <span class="mx-1 h-5 w-px bg-surface-gray-4" />
          <TabButtons :model-value="settings.view" :options="views" @update:model-value="(view) => remember({ view })" />
          <Button variant="ghost" icon="lucide-panel-right" :aria-label="__('Preview pane')" :title="__('Preview pane')" @click="remember({ preview: settings.preview ? 0 : 1 })" />
        </template>
      </div>
      <div v-if="!picker" class="flex flex-wrap items-center gap-0.5 border-b border-outline-gray-1 px-2 py-1.5">
        <Dropdown :options="newMenu">
          <template #trigger>
            <Button variant="solid" icon-left="lucide-plus" icon-right="lucide-chevron-down" :label="__('New')" :disabled="!canNew" />
          </template>
        </Dropdown>
        <span class="mx-1 h-5 w-px bg-surface-gray-4" />
        <template v-for="one in commands" :key="one.act">
          <Button v-if="one.label" variant="ghost" :icon-left="one.icon" :label="one.label" :disabled="one.off" @click="act(one.act)" />
          <Button v-else variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" @click="act(one.act)" />
        </template>
        <span class="flex-1" />
        <TabButtons :model-value="settings.view" :options="views" @update:model-value="(view) => remember({ view })" />
        <Button variant="ghost" icon="lucide-panel-right" :aria-label="__('Preview pane')" :title="__('Preview pane')" @click="remember({ preview: settings.preview ? 0 : 1 })" />
      </div>
    </template>

    <div class="flex min-h-0 flex-1" :class="{ 'px-2.5 pb-2.5': win }">
      <ContextMenu :options="picker ? [] : menu" class="min-w-0 flex-1">
        <template #trigger>
          <div class="h-full min-w-0 flex-1">
            <CloudItems
              ref="list"
              :card="!!win"
              :items="sorted"
              :view="settings.view"
              :sort="{ key: settings.sort, asc: !!settings.asc }"
              :selected="selected"
              :cut="cutIds"
              :focus-id="focusId"
              :renaming="renaming"
              :kind="kind"
              :where-head="whereHead"
              :empty="emptyText(kind, !!search)"
              :scoped="!!search && kind !== 'root' && !room"
              :searching="!!search"
              :everywhere="everywhere"
              :here-name="here?.name || __('Files')"
              :here="node"
              :drop-on="dropOn"
              :intake-on="intakeOn()"
              @pick="pick"
              @open="(id) => openItems([find(id)])"
              @sort="sortBy"
              @space="space"
              @menu="menuFor"
              @renamed="renamed"
              @everywhere="toggleEverywhere"
              @dragstart="dragStart"
              @dragend="dragEnd"
              @dragover="over"
              @dragleave="leave"
              @drop="drop"
            >
              <template #action>
                <template v-for="one in commands.filter((c) => !c.off)" :key="one.act">
                  <Button v-if="one.label" size="sm" variant="ghost" :icon-left="one.icon" :label="one.label" @click="act(one.act)" />
                  <Button v-else size="sm" variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" @click="act(one.act)" />
                </template>
              </template>
            </CloudItems>
          </div>
        </template>
      </ContextMenu>
      <div v-if="!win && settings.preview" class="w-72 shrink-0 overflow-auto border-s border-outline-gray-1 max-md:hidden">
        <CloudPreview :chosen="chosen" :items="items" :node="node" :here-name="here?.name || ''" :picker="!!picker" @changed="refresh" />
      </div>
    </div>

    <div v-if="!win" class="border-t border-outline-gray-1 px-3 py-1 text-sm text-ink-gray-5">{{ status }}</div>

    <div class="absolute bottom-3 end-3 z-10">
      <CloudUploads :rows="uploads" @close="uploads = []" />
    </div>
    <input ref="pickFiles" type="file" multiple hidden @change="picked($event)" />
    <input ref="pickFolder" type="file" webkitdirectory hidden @change="picked($event)" />
    <input ref="pickVersion" type="file" hidden @change="pickedVersion($event)" />
  </div>
</template>

<script setup>
// OneCloud (one_storage/api.py) as Explorer has it: the folders as a tree,
// what is in the one open as Details or Tiles, what is chosen beside it, and
// the keys, menus, cut, copy and paste, rename in place and dragging that
// Explorer has. On its own page it is on the window (onedesk/one_interface/AGENTS.md): the
// tree in the nav pane, the commands in the command row, the chosen file in
// the details pane, the path in the breadcrumbs and the count in the status
// row. In a record's files dialog (`room`) and in the picker (`picker`) it
// keeps them in itself, in the window's order: the address row, then the
// commands (none in the picker, whose view toggles end the address row).
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, ContextMenu, Dropdown, TabButtons, TextInput } from "frappe-ui";

import {
  InterfacePart,
  __,
  aiMoved,
  alert,
  call,
  confirm,
  copyText,
  csrf,
  get,
  goTo,
  goToUrl,
  hasRole,
  intakeOn,
  listenIn,
  onedesk,
  openTab,
  requires,
  setCrumbs,
  userSettings,
  interfaceCan,
  interfaceHandles,
  interfaceHeading,
  interfaceMeters,
  interfaceSearch,
  interfaceStatus,
  interfaceTree,
} from "../kit";
import { sizes as slideSizes } from "../slide/shim/frame.js";
import { API, SHEETS, UPLOAD, across, count, emptyText, extension, filed, iconOf, kindOf, sizeText, stored, takes, typeOf } from "./cloud";
import CloudItems from "./CloudItems.vue";
import CloudPreview from "./CloudPreview.vue";
import CloudUploads from "./CloudUploads.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  win: { type: Object, default: null },
  onTitle: Function,
  room: { type: String, default: null },
  picker: { type: Object, default: null },
  onListed: Function,
});

const node = ref(null);
const items = ref([]);
const trail = ref([]);
const watching = ref([]);
const can = reactive({ add: false, folder: false, library: false, mount: false });
const selected = reactive(new Set());
const focusId = ref(null);
const clipboard = ref(null);
const search = ref("");
const typed = ref("");
const everywhere = ref(false);
const past = ref([]);
const ahead = ref([]);
const kids = reactive({});
const openInTree = reactive(new Set(["@my", "@company"]));
const settings = reactive({ view: "details", sort: "name", asc: 1, preview: 1 });
const renaming = ref(null);
const dragging = ref(null);
const dropOn = ref(null);
const uploads = ref([]);
const menu = ref([]);
const root = ref(null);
const list = ref(null);
const searchInput = ref(null);
const pickFiles = ref(null);
const pickFolder = ref(null);
const pickVersion = ref(null);
let anchor = null;
let reveal = null;
let versionOf = null;
let ready = false;
let room = props.room;

const kind = computed(() => kindOf(node.value || ""));
const here = computed(() => trail.value[trail.value.length - 1] || null);
const chosen = computed(() => items.value.filter((one) => selected.has(one.id)));
// The path off the window: in a record's files it starts at the record, which
// the dialog's title already names the way in to.
const crumbs = computed(() => {
  if (!room) return trail.value;
  const from = trail.value.findIndex((one) => same(one.id));
  return from < 0 ? trail.value : trail.value.slice(from);
});

const cutIds = computed(() => new Set(clipboard.value?.mode === "cut" ? clipboard.value.ids : []));
const canNew = computed(() => can.add || can.library || can.mount || kind.value === "requests");
const searchPlaceholder = computed(() =>
  everywhere.value || kind.value === "root" ? __("Search everywhere") : __("Search {0}", [here.value ? here.value.name : __("Files")])
);
const whereHead = computed(() => {
  if (search.value) return "";
  return (
    { shared: __("Shared by"), libraries: __("Your role"), recent: __("Folder"), starred: __("Folder"), network: __("Type"), requests: __("Progress"), request: __("File · From") }[
      kind.value
    ] || ""
  );
});

const views = [
  { value: "details", icon: "lucide-layout-list", label: __("Details") },
  { value: "tiles", icon: "lucide-layout-grid", label: __("Tiles") },
];

const sorted = computed(() => {
  const { sort } = settings;
  const way = settings.asc ? 1 : -1;
  const shown = kind.value === "libraries" ? items.value.map((one) => ({ ...one, where: one.role ? __(one.role) : "" })) : items.value;
  const value = (item) => {
    if (sort === "size") return item.folder ? -1 : item.size || 0;
    if (sort === "modified") return (kind.value === "bin" ? item.deleted : item.modified) || "";
    if (sort === "type") return typeOf(item);
    if (sort === "where") return (item.where || "").toLowerCase();
    return (item.name || "").toLowerCase();
  };
  if (["root", "records"].includes(kind.value) && sort === "name" && way === 1) return shown.slice();
  return shown.slice().sort((a, b) => {
    if (a.folder !== b.folder) return a.folder ? -1 : 1;
    const x = value(a);
    const y = value(b);
    if (x < y) return -way;
    if (x > y) return way;
    return (a.name || "").localeCompare(b.name || "") * way;
  });
});

const status = computed(() => {
  let text = count(items.value.length, __("1 item"), __("{0} items"));
  if (chosen.value.length) {
    const bytes = chosen.value.reduce((sum, one) => sum + (one.folder ? 0 : one.size || 0), 0);
    text += "  ·  " + count(chosen.value.length, __("1 item selected"), __("{0} items selected"));
    if (bytes) text += "  " + sizeText(bytes);
  }
  return text;
});

// ---- settings ----

function remember(change) {
  Object.assign(settings, change);
  userSettings.save("File", "OneCloud", { ...settings });
}

function sortBy(key) {
  remember({ sort: key, asc: settings.sort === key ? (settings.asc ? 0 : 1) : 1 });
}

// ---- where we are ----

const find = (id) => items.value.find((one) => one.id === id);
const libraryHere = () => (trail.value.length > 2 && trail.value[1].id === "@libraries" ? trail.value[2] : null);
const recordHere = () => {
  const parts = (node.value || "").split("/");
  return parts[0] === "@records" && parts.length === 3 ? [parts[1], parts[2]] : null;
};

function same(id) {
  return id === room || (room.startsWith("@own/") && id === `@records/Project/${room.slice(5)}`);
}

function holds(id) {
  if (same(id)) return true;
  const from = trail.value.findIndex((one) => same(one.id));
  if (from < 0) return false;
  return trail.value.slice(from).some((one) => one.id === id) || items.value.some((one) => one.id === id && one.folder);
}

function wanted() {
  if (props.picker) return node.value || props.picker.start || "@my";
  return room || props.query.node || "@my";
}

function go(id) {
  if (id === node.value && !search.value) return;
  setSearch("");
  if (props.picker) {
    if (node.value) past.value.push(node.value);
    ahead.value = [];
    return open(id);
  }
  if (room) {
    if (!holds(id)) return goToUrl(`/desk/onecloud?node=${encodeURIComponent(id)}`);
    if (same(id)) id = room;
    if (id === node.value) return refresh();
    if (node.value) past.value.push(node.value);
    ahead.value = [];
    return open(id);
  }
  goToUrl(`/desk/onecloud?node=${encodeURIComponent(id)}`);
}

async function open(id) {
  node.value = id;
  if (!props.picker && !room && props.query.file) reveal = props.query.file;
  selected.clear();
  anchor = focusId.value = null;
  await refresh();
  list.value?.focus();
}

let asking = 0;
async function refresh() {
  const mine = ++asking;
  let answer;
  try {
    answer = await call(API + "listing", { node: node.value, search: search.value || null, everywhere: search.value && everywhere.value ? 1 : 0 });
  } catch (e) {
    if (mine !== asking) return;
    if (node.value !== "@my") return go("@my");
    throw e;
  }
  if (mine !== asking) return;
  items.value = answer.items || [];
  trail.value = answer.trail || [];
  watching.value = answer.watch || [];
  can.add = !!answer.can_add;
  can.folder = !!answer.can_make_folder;
  can.library = !!answer.can_make_library;
  can.mount = !!answer.can_make_mount;
  const live = new Set(items.value.map((one) => one.id));
  for (const id of [...selected]) if (!live.has(id)) selected.delete(id);
  if (!room) drawTree();
  props.onListed?.(items.value.length);
  if (reveal && live.has(reveal)) {
    pick(reveal, {});
    const id = reveal;
    setTimeout(() => list.value?.reveal(id));
  }
  reveal = null;
  tellWindow();
}

// The window says where we are: the path in the breadcrumbs, Up, the count.
function tellWindow() {
  if (!props.win) return;
  const last = trail.value.length - 1;
  setCrumbs(
    trail.value.map((one, at) => ({ label: one.name, ...(at < last ? { href: `/desk/onecloud?node=${encodeURIComponent(one.id)}` } : {}) })),
    last >= 0 ? trail.value[last].name : __("OneCloud")
  );
  interfaceCan(props.win, { up: trail.value.length > 1 });
  searchBox?.placeholder(searchPlaceholder.value);
}

watch(status, (text) => interfaceStatus(props.win, text));

// OneAI follows the folder and the one file chosen (oneai.js, where).
watch([node, chosen], () => {
  if (props.picker || room) return;
  const one = chosen.value.length === 1 && !chosen.value[0].folder && filed(chosen.value[0]) ? chosen.value[0] : null;
  const cloud = onedesk().cloud;
  if (!cloud) return;
  const was = cloud.where;
  cloud.where = { folder: node.value || "", file: one ? one.id : "", label: one ? one.name : "" };
  if (!was || was.folder !== cloud.where.folder || was.file !== cloud.where.file) aiMoved();
});

watch(chosen, (now) => props.picker?.onSelect?.(now.filter((one) => !one.folder)));

// ---- the tree ----
// The window's (window/nav_tree.js), in the nav pane on the page and in the
// box the picker's dialog gives it: the places at the top (My Files, Company,
// Libraries, Records, the Recycle Bin), each folder opened as far as the
// reader opened it.

const treeRows = computed(() => {
  const out = [];
  const walk = (list, depth) => {
    for (const one of list || []) {
      const leaf = one.id === "@bin" || (one.record && !one.doctype);
      const open = openInTree.has(one.id);
      out.push({
        id: one.id,
        label: one.name,
        icon: iconOf(one),
        depth,
        open: leaf ? undefined : open,
        active: one.id === node.value,
        href: props.win ? `/desk/onecloud?node=${encodeURIComponent(one.id)}` : "",
      });
      if (open && !leaf && kids[one.id]) walk(kids[one.id], depth + 1);
    }
  };
  walk(kids["@root"], 0);
  return out;
});

const tree = room
  ? null
  : interfaceTree(props.win || (props.picker && props.picker.nav), {
      label: __("Folders"),
      pick: (id) => go(id),
      twist,
      over: props.picker
        ? null
        : (id, event) => {
            over(event, id);
            return Boolean(dropOn.value) && dropOn.value === targetOf(id);
          },
      leave: () => (dropOn.value = null),
      drop: props.picker ? null : (id, event) => drop(event, id),
    });
if (tree) watch(treeRows, (rows) => tree.set(rows), { immediate: true });

// How full the workspace is, at the foot of the rail (api.capacity); asked
// again when its files change.
async function measure() {
  if (props.win) interfaceMeters(props.win, await get(API + "capacity"));
}
measure();

async function drawTree() {
  if (!kids["@root"]) kids["@root"] = await call(API + "folders", { node: "@root" });
  for (const one of trail.value.slice(1, -1)) openInTree.add(one.id);
  for (const id of openInTree) {
    if (kids[id]) continue;
    try {
      kids[id] = await call(API + "folders", { node: id });
    } catch (e) {
      openInTree.delete(id);
    }
  }
}

function forget(...ids) {
  if (!ids.length) Object.keys(kids).forEach((id) => delete kids[id]);
  ids.filter(Boolean).forEach((id) => delete kids[id]);
}

function twist(id) {
  if (openInTree.has(id)) openInTree.delete(id);
  else openInTree.add(id);
  drawTree();
}

// ---- choosing ----

function pick(id, event) {
  const order = sorted.value.map((one) => one.id);
  if (event.button === 2 && selected.has(id)) return;
  if (event.button > 2) return;
  if (event.shiftKey && anchor && order.includes(anchor)) {
    const [a, b] = [order.indexOf(anchor), order.indexOf(id)].sort((x, y) => x - y);
    if (!(event.ctrlKey || event.metaKey)) selected.clear();
    order.slice(a, b + 1).forEach((one) => selected.add(one));
  } else if (event.ctrlKey || event.metaKey) {
    if (selected.has(id)) selected.delete(id);
    else selected.add(id);
    anchor = id;
  } else {
    selected.clear();
    selected.add(id);
    anchor = id;
  }
  focusId.value = id;
}

function space(event) {
  if (event.ctrlKey || event.metaKey || event.shiftKey) return;
  selected.clear();
  focusId.value = null;
}

function setSearch(value) {
  search.value = value;
  typed.value = value;
  if (!value) everywhere.value = false;
  searchBox?.set(value);
}

function toggleEverywhere() {
  everywhere.value = !everywhere.value;
  refresh();
}

let typing = null;
watch(typed, (value) => {
  if (props.win) return;
  clearTimeout(typing);
  typing = setTimeout(() => {
    search.value = value.trim();
    refresh();
  }, 300);
});

function searchKey(event) {
  if (event.key === "Escape") {
    setSearch("");
    refresh();
    list.value?.focus();
  }
  if (event.key === "ArrowDown") list.value?.focus();
  event.stopPropagation();
}

// ---- what can be done ----

const commands = computed(() => {
  const picked = chosen.value;
  const allStored = picked.length && picked.every((one) => stored(one));
  const k = kind.value;
  const bare = (act, icon, title, on) => ({ act, icon, title, off: !on });
  const out = [
    bare("cut", "lucide-scissors", __("Cut"), allStored && k !== "bin"),
    bare("copy", "lucide-copy", __("Copy"), allStored && k !== "bin"),
    bare("paste", "lucide-clipboard-paste", __("Paste"), can.add && !!clipboard.value),
    bare("rename", "lucide-pencil", __("Rename"), picked.length === 1 && stored(picked[0]) && k !== "bin" && k !== "record"),
    bare("share", "lucide-user-plus", __("Share"), picked.length === 1 && filed(picked[0]) && k !== "bin"),
    bare("download", "lucide-download", __("Download"), picked.length && picked.every((one) => !one.folder && one.url)),
    bare("delete", "lucide-trash-2", __("Delete"), allStored),
  ];
  if (k === "bin") {
    out.push({ act: "restore", icon: "lucide-rotate-ccw", label: __("Restore"), off: !picked.length });
    out.push({ act: "empty-bin", icon: "lucide-trash-2", label: __("Empty Recycle Bin"), off: !items.value.length });
  }
  if (!room && (k === "record" || k === "records" || picked.some((one) => one.record))) {
    out.push({ act: "open-record", icon: "lucide-external-link", label: __("Open record"), off: !(picked[0]?.record || k === "record") });
  }
  if (libraryHere()) out.push({ act: "members", icon: "lucide-users", label: __("Members"), off: false });
  return out;
});

const asMenu = (groups) =>
  groups
    .map((group) => group.filter(Boolean))
    .filter((group) => group.length)
    .map((group) => ({
      group: "",
      hideLabel: true,
      options: group.map(([act, icon, label, on, theme]) => ({ label, icon, disabled: !on, theme: theme || undefined, onClick: () => act_(act) })),
    }));

const act_ = (name) => act(name);

const newMenu = computed(() => {
  const k = kind.value;
  const local = !(node.value || "").startsWith("@mount");
  if (k === "libraries") return asMenu([[["new-library", "lucide-library-big", __("Library"), can.library]]]);
  if (k === "network") return asMenu([[["new-mount", "lucide-server", __("Server connection"), can.mount]]]);
  if (k === "requests") return asMenu([[["new-request", "lucide-inbox", __("File request"), true]]]);
  return asMenu([
    [
      ["new-folder", "lucide-folder-plus", __("Folder"), can.folder],
      ["new-workbook", "lucide-file-spreadsheet", __("Workbook"), can.add && local],
      ["new-document", "lucide-file-text", __("Document"), can.add && local],
      ["new-presentation", "lucide-presentation", __("Presentation"), can.add && local],
    ],
    [
      ["upload-files", "lucide-upload", __("Upload files"), can.add],
      ["upload-folder", "lucide-folder-up", __("Upload folder"), can.add && k !== "record"],
    ],
    [["new-request", "lucide-inbox", __("File request"), can.add && local]],
  ]);
});

function itemMenu() {
  const picked = chosen.value;
  const one = picked.length === 1 ? picked[0] : null;
  const allStored = picked.every((item) => stored(item));
  const files = picked.filter((item) => !item.folder && item.url);
  if (one && one.request) return asMenu([[["open", "lucide-folder-open", __("Open"), true], ["request-progress", "lucide-list-checks", __("Progress…"), true]]]);
  if (one && one.mount) {
    return asMenu([
      [
        ["open", "lucide-folder-open", __("Open"), true],
        ["mount-edit", "lucide-settings", __("Edit connection…"), true],
        ["mount-drop", "lucide-unplug", __("Disconnect"), true, "red"],
      ],
    ]);
  }
  if (kind.value === "bin") return asMenu([[["restore", "lucide-rotate-ccw", __("Restore"), true], ["purge", "lucide-trash-2", __("Delete permanently"), true, "red"]]]);
  return asMenu([
    [
      ["open", one && one.folder ? "lucide-folder-open" : "lucide-external-link", __("Open"), true],
      one && one.parent && search.value ? ["open-location", "lucide-folder-open", __("Open file location"), true] : null,
      one && one.record && !room ? ["open-record", "lucide-external-link", __("Open record"), true] : null,
      files.length === picked.length ? ["download", "lucide-download", __("Download"), true] : null,
      one && one.workbook ? ["download-xlsx", "lucide-file-spreadsheet", __("Download as Excel"), true] : null,
      one && one.workbook ? ["download-csv", "lucide-file-text", __("Download as CSV"), true] : null,
      files.length === picked.length ? ["copy-link", "lucide-link", __("Copy link"), true] : null,
    ],
    [
      ["cut", "lucide-scissors", __("Cut"), allStored],
      ["copy", "lucide-copy", __("Copy"), allStored],
      ["paste-into", "lucide-clipboard-paste", __("Paste into folder"), !!(clipboard.value && one && one.folder)],
    ],
    [
      ["share", "lucide-user-plus", __("Share…"), !!(one && filed(one))],
      picked.every((item) => item.starred)
        ? ["unstar", "lucide-star-off", __("Remove star"), picked.every((item) => filed(item))]
        : ["star", "lucide-star", __("Star"), picked.every((item) => filed(item))],
      one && !one.folder && filed(one) ? ["new-version", "lucide-upload", __("Upload new version"), !one.record] : null,
      one && one.folder && !one.virtual ? ["drive", "lucide-hard-drive", __("Connect as a drive…"), true] : null,
      one && !one.folder && intakeOn() && filed(one) && !(one.record && one.record[0] === "Communication") ? ["read-file", "lucide-scan-text", __("Read with OneAI"), true] : null,
      ["rename", "lucide-pencil", __("Rename"), !!(one && allStored) && kind.value !== "record"],
      ["delete", "lucide-trash-2", __("Delete"), allStored, "red"],
    ],
  ]);
}

function spaceMenu() {
  const local = !(node.value || "").startsWith("@mount");
  if (kind.value === "libraries") return asMenu([[["new-library", "lucide-library-big", __("New library"), can.library]], [["refresh", "lucide-refresh-cw", __("Refresh"), true]]]);
  if (kind.value === "network") return asMenu([[["new-mount", "lucide-server", __("Connect server"), can.mount]], [["refresh", "lucide-refresh-cw", __("Refresh"), true]]]);
  return asMenu([
    [
      ["new-folder", "lucide-folder-plus", __("New folder"), can.folder],
      ["new-workbook", "lucide-file-spreadsheet", __("New Workbook"), can.add && local],
      ["new-document", "lucide-file-text", __("New Document"), can.add && local],
      ["new-presentation", "lucide-presentation", __("New Presentation"), can.add && local],
      ["upload-files", "lucide-upload", __("Upload files"), can.add],
      ["upload-folder", "lucide-folder-up", __("Upload folder"), can.add && kind.value !== "record"],
      ["paste", "lucide-clipboard-paste", __("Paste"), can.add && !!clipboard.value],
    ],
    [
      ["view-details", "lucide-layout-list", __("Details"), true],
      ["view-tiles", "lucide-layout-grid", __("Tiles"), true],
    ],
    [
      ["sort-name", "lucide-arrow-up-down", __("Sort by name"), true],
      ["sort-modified", "lucide-arrow-up-down", __("Sort by date"), true],
      ["sort-type", "lucide-arrow-up-down", __("Sort by type"), true],
      ["sort-size", "lucide-arrow-up-down", __("Sort by size"), true],
    ],
    [
      ["drive-here", "lucide-hard-drive", __("Connect as a drive…"), true],
      ["refresh", "lucide-refresh-cw", __("Refresh"), true],
    ],
  ]);
}

function menuFor(event, id) {
  if (props.picker) return event.preventDefault();
  if (id && !selected.has(id)) pick(id, {});
  if (!id) selected.clear();
  menu.value = id ? itemMenu() : spaceMenu();
}

// ---- acting ----

const cloud = () => onedesk().cloud;
const dialogsGo = (id, place) => {
  if (place) forget(place);
  go(id);
};

async function act(name) {
  const picked = chosen.value;
  const ids = picked.filter((one) => stored(one)).map((one) => one.id);
  const k = kind.value;
  switch (name) {
    case "back":
      if ((props.picker || room) && past.value.length) {
        ahead.value.push(node.value);
        return open(past.value.pop());
      }
      return history.back();
    case "forward":
      if ((props.picker || room) && ahead.value.length) {
        past.value.push(node.value);
        return open(ahead.value.pop());
      }
      return history.forward();
    case "up":
      if (trail.value.length > 1) go(trail.value[trail.value.length - 2].id);
      return;
    case "refresh":
      forget();
      return refresh();
    case "view-details":
      return remember({ view: "details" });
    case "view-tiles":
      return remember({ view: "tiles" });
    case "new-folder":
      return can.folder && newFolder();
    case "new-workbook":
      return newFrom("onedesk.one_sheet.templates.listed", __("Blank Workbook"), "onedesk.one_sheet.api.make", "workbook");
    case "new-document":
      return newFrom("onedesk.one_doc.templates.listed", __("Blank Document"), "onedesk.one_doc.api.make", "document");
    case "new-presentation":
      return newPresentation();
    case "new-library":
      return cloud().new_library(dialogsGo);
    case "new-mount":
      return cloud().mount(null, dialogsGo);
    case "new-request":
      return cloud().request({ node: node.value, kind: k, trail: trail.value }, dialogsGo);
    case "request-progress":
      return cloud().request_progress(picked[0].id.split("/")[1], (place) => (forget(place), refresh()));
    case "mount-edit":
      return cloud().mount(picked[0], dialogsGo);
    case "mount-drop":
      return confirm(__("Disconnect {0}? Files on the server stay as they are.", [picked[0].name]), async () => {
        await call("onedesk.one_storage.mounts.disconnect", { node: picked[0].id });
        forget("@mounts");
        refresh();
      });
    case "members": {
      const lib = libraryHere();
      if (lib) cloud().members({ id: lib.id, name: lib.name });
      return;
    }
    case "upload-files":
      return pickFiles.value?.click();
    case "upload-folder":
      return pickFolder.value?.click();
    case "cut":
    case "copy":
      if (!ids.length || k === "bin") return;
      clipboard.value = { mode: name, ids, from: node.value };
      return alert(name === "cut" ? count(ids.length, __("Cut 1 item"), __("Cut {0} items")) : count(ids.length, __("Copied 1 item"), __("Copied {0} items")), "blue");
    case "paste":
      return paste(node.value);
    case "paste-into":
      return paste(picked[0].id);
    case "rename":
      if (picked.length === 1 && stored(picked[0]) && !["bin", "record"].includes(k)) renaming.value = picked[0].id;
      return;
    case "share":
      if (picked.length === 1 && filed(picked[0])) cloud().share(picked[0], refresh);
      return;
    case "read-file":
      return cloud().read_file(picked[0]);
    case "drive":
      return cloud().drive(picked[0].id, picked[0].name);
    case "drive-here": {
      const shown = ["@root", "@recent", "@starred", "@bin", "@mounts"].includes(node.value) || node.value.startsWith("@mount/") ? "@root" : node.value;
      return cloud().drive(shown, here.value ? here.value.name : __("Files"));
    }
    case "star":
    case "unstar":
      await call("onedesk.one_storage.history.star", { nodes: ids, on: name === "star" ? 1 : 0 });
      return refresh();
    case "new-version":
      if (picked.length !== 1 || picked[0].folder) return;
      versionOf = picked[0];
      return pickVersion.value?.click();
    case "download":
      return download(picked.filter((one) => !one.folder && one.url));
    case "download-xlsx":
    case "download-csv":
      return goTo("workbook", picked[0].workbook, { export: name.slice(9) });
    case "copy-link":
      return copyText(picked.map((one) => document.location.origin + one.url).join("\n"));
    case "open":
      return openItems(picked);
    case "open-location":
      reveal = picked[0].id;
      return go(picked[0].parent);
    case "open-record": {
      const record = picked[0]?.record || recordHere();
      if (record) goTo("Form", record[0], record[1]);
      return;
    }
    case "delete":
      if (!ids.length) return;
      if (k === "bin") return act("purge");
      return remove(picked);
    case "restore":
      if (!ids.length) return;
      await call(API + "restore", { nodes: ids });
      alert(count(ids.length, __("Restored 1 item"), __("Restored {0} items")));
      forget();
      return refresh();
    case "purge":
      if (!ids.length) return;
      return confirm(
        ids.length === 1 ? __("Delete {0} permanently? This can't be undone.", [picked[0].name]) : __("Delete {0} items permanently? This can't be undone.", [ids.length]),
        async () => {
          await call(API + "purge", { nodes: ids });
          forget();
          refresh();
        }
      );
    case "empty-bin":
      return confirm(__("Empty Recycle Bin? Everything in it is deleted permanently."), async () => {
        await call(API + "empty_bin");
        refresh();
      });
    case "sort-name":
    case "sort-modified":
    case "sort-type":
    case "sort-size":
      return remember({ sort: name.slice(5), asc: name === "sort-modified" || name === "sort-size" ? 0 : 1 });
  }
}

function openItems(list) {
  list = list.filter(Boolean);
  if (!list.length) return;
  const folder = list.find((one) => one.folder);
  if (folder && list.length === 1) return go(folder.id);
  if (props.picker) return props.picker.onPick?.(list.filter((one) => !one.folder));
  const one = list.length === 1 ? list[0] : null;
  if (one?.workbook) return goTo("workbook", one.workbook);
  if (one?.document) return goTo("document", one.document);
  if (one?.presentation) return goTo("presentation", one.presentation);
  // An Excel or CSV file opens in OneWorkbook and a Word file in OneWriter,
  // each saved back into itself.
  if (one && !one.folder && SHEETS.includes(extension(one))) return call("onedesk.one_sheet.api.open_file", { file: one.id }).then((made) => goTo("workbook", made.workbook));
  if (one && !one.folder && extension(one) === "docx") return call("onedesk.one_doc.word.open_file", { file: one.id }).then((made) => goTo("document", made.document));
  list.filter((item) => !item.folder && item.url).forEach((item) => openTab(item.url));
}

function download(list) {
  list.forEach((one, at) =>
    setTimeout(() => {
      const a = document.createElement("a");
      a.href = one.url.startsWith("/api/") ? `${one.url}&download=1` : one.url;
      a.download = one.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, at * 400)
  );
}

async function newFrom(templates, blank, make, route) {
  const template = await onedesk().table_workbook.pick(await call(templates), blank);
  if (template === null) return;
  const made = await call(make, { parent: node.value, template: template || null });
  forget(node.value);
  goTo(route, made[route]);
}

// a presentation is asked its size as well as its template (one_slide/resize.py)
async function newPresentation() {
  const sizes = slideSizes();
  const said = await onedesk().table_workbook.pick(await call("onedesk.one_slide.api.listed"), __("Blank Presentation"), sizes);
  if (!said) return;
  // "As It Was Made" has no size: sent empty, the server refuses it as a number
  const size = said.width && said.height ? { width: said.width, height: said.height } : {};
  const made = await call("onedesk.one_slide.api.make", { parent: node.value, template: said.template || null, ...size });
  forget(node.value);
  goTo("presentation", made.presentation);
}

async function newFolder() {
  const made = await call(API + "make_folder", { parent: node.value, name: __("New folder") });
  forget(node.value);
  await refresh();
  selected.clear();
  selected.add(made.id);
  focusId.value = anchor = made.id;
  renaming.value = made.id;
}

async function renamed(item, name) {
  if (renaming.value !== item.id) return;
  renaming.value = null;
  const want = (name || "").trim();
  if (name !== null && want && want !== item.name) {
    try {
      await call(API + "rename", { node: item.id, name: want });
    } catch (e) {
      // frappe has said why
    }
    forget();
  }
  await refresh();
  list.value?.focus();
}

function remove(list) {
  const attached = list.filter((one) => (one.record && !one.folder) || one.remote);
  const doIt = async () => {
    const said = await call(API + "delete", { nodes: list.map((one) => one.id) });
    const binned = (said && +said.binned) || 0;
    if (binned) alert(count(binned, __("Moved 1 item to the Recycle Bin"), __("Moved {0} items to the Recycle Bin")), "blue");
    forget();
    refresh();
  };
  if (!attached.length) return doIt();
  if (attached.some((one) => one.remote)) {
    return confirm(
      attached.length === 1 ? __("Delete {0} from the server? This can't be undone.", [attached[0].name]) : __("Delete {0} items from the server? This can't be undone.", [attached.length]),
      doIt
    );
  }
  confirm(
    attached.length === 1 ? __("Remove {0} from its record? This can't be undone.", [attached[0].name]) : __("Remove {0} files from their records? This can't be undone.", [attached.length]),
    doIt
  );
}

async function paste(target) {
  if (!clipboard.value) return;
  const { mode, ids } = clipboard.value;
  await transfer(ids, target, mode === "cut" ? "move" : "copy");
  if (mode === "cut") clipboard.value = null;
}

async function transfer(ids, target, how) {
  if (!ids.length || ids.includes(target)) return;
  const done = await call(how === "move" ? API + "move" : API + "copy", { nodes: ids, target });
  const n = (done && done.length) || 0;
  alert(how === "move" ? count(n, __("Moved 1 item"), __("Moved {0} items")) : count(n, __("Copied 1 item"), __("Copied {0} items")));
  forget();
  refresh();
}

// ---- keys, as Explorer has them ----

function key(event) {
  if (event.target.closest?.("input, textarea, [contenteditable]")) return;
  const ctrl = event.ctrlKey || event.metaKey;
  const k = event.key;
  const done = (then) => {
    event.preventDefault();
    event.stopPropagation();
    then();
  };
  if (k === "F5" || (ctrl && k === "r")) return done(() => act("refresh"));
  if ((event.altKey && k === "ArrowLeft") || k === "Backspace") return done(() => act("back"));
  if (event.altKey && k === "ArrowRight") return done(() => act("forward"));
  if (event.altKey && k === "ArrowUp") return done(() => act("up"));
  const changes = (ctrl && ["c", "x", "v"].includes(k)) || ["F2", "Delete"].includes(k) || (ctrl && event.shiftKey && k.toLowerCase() === "n");
  if (props.picker && changes) return;
  if (ctrl && event.shiftKey && k.toLowerCase() === "n") return done(() => act("new-folder"));
  if (ctrl && event.shiftKey && k.toLowerCase() === "f" && !room) {
    return done(() => {
      everywhere.value = true;
      if (search.value) refresh();
      focusSearch();
    });
  }
  if ((ctrl && k === "f") || k === "F3") return done(focusSearch);
  if (ctrl && k === "a") return done(() => items.value.forEach((one) => selected.add(one.id)));
  if (ctrl && k === "c") return done(() => act("copy"));
  if (ctrl && k === "x") return done(() => act("cut"));
  if (ctrl && k === "v") return done(() => act("paste"));
  if (k === "F2") return done(() => act("rename"));
  if (k === "Delete") return done(() => act(event.shiftKey || kind.value === "bin" ? "purge" : "delete"));
  if (k === "Enter") return done(() => openItems(chosen.value));
  if (k === "Escape") {
    return done(() => {
      clipboard.value = null;
      selected.clear();
    });
  }
  const moves = { ArrowDown: 1, ArrowUp: -1, ArrowRight: 1, ArrowLeft: -1, Home: "first", End: "last" };
  if (!(k in moves) || event.altKey) return;
  event.preventDefault();
  const order = sorted.value.map((one) => one.id);
  if (!order.length) return;
  let at = order.indexOf(focusId.value);
  const across = settings.view === "tiles" ? list.value?.columnsAcross() || 1 : 1;
  if (moves[k] === "first") at = 0;
  else if (moves[k] === "last") at = order.length - 1;
  else if (at < 0) at = 0;
  else if (settings.view === "details" && (k === "ArrowLeft" || k === "ArrowRight")) return;
  else at += moves[k] * (k === "ArrowDown" || k === "ArrowUp" ? across : 1);
  at = Math.max(0, Math.min(order.length - 1, at));
  pick(order[at], { shiftKey: event.shiftKey });
  list.value?.reveal(order[at]);
}

function focusSearch() {
  if (searchBox) return searchBox.focus();
  searchInput.value?.$el?.querySelector("input")?.focus();
}

// ---- dragging, within OneCloud and in from the computer ----

function targetOf(id) {
  if (id && takes(id)) return id;
  if (!id && can.add) return node.value;
  return null;
}

function dragStart(event, id) {
  if (!selected.has(id)) pick(id, {});
  const ids = chosen.value.filter((one) => stored(one)).map((one) => one.id);
  if (!ids.length) return event.preventDefault();
  dragging.value = ids;
  event.dataTransfer.effectAllowed = "copyMove";
  event.dataTransfer.setData("text/plain", chosen.value.map((one) => one.name).join("\n"));
}

function dragEnd() {
  dragging.value = null;
  dropOn.value = null;
}

const copying = (event, target) =>
  event.ctrlKey || event.metaKey || target.startsWith("@records/") || kind.value === "record" || across(node.value, target);

function over(event, id) {
  if (props.picker) return;
  const outside = !dragging.value && [...event.dataTransfer.types].includes("Files");
  if (!outside && !dragging.value) return;
  const target = targetOf(id);
  if (!target || (dragging.value && (dragging.value.includes(target) || target === node.value))) {
    event.dataTransfer.dropEffect = "none";
    dropOn.value = null;
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  event.dataTransfer.dropEffect = outside || copying(event, target) ? "copy" : "move";
  dropOn.value = target;
}

function leave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) dropOn.value = null;
}

async function drop(event, id) {
  if (props.picker) return;
  event.preventDefault();
  event.stopPropagation();
  dropOn.value = null;
  const target = targetOf(id);
  if (!target) return;
  if (dragging.value) {
    const ids = dragging.value;
    dragging.value = null;
    return transfer(ids, target, copying(event, target) ? "copy" : "move");
  }
  const list = await dropped(event.dataTransfer);
  if (list.length) upload(list, target);
}

async function dropped(transferred) {
  const entries = [...transferred.items].map((one) => one.webkitGetAsEntry && one.webkitGetAsEntry()).filter(Boolean);
  if (!entries.length) return [...transferred.files].map((file) => ({ file, path: file.name }));
  const out = [];
  const walk = async (entry, prefix) => {
    if (entry.isFile) {
      const file = await new Promise((ok, no) => entry.file(ok, no));
      out.push({ file, path: prefix + file.name });
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      let batch;
      do {
        batch = await new Promise((ok, no) => reader.readEntries(ok, no));
        for (const child of batch) await walk(child, `${prefix}${entry.name}/`);
      } while (batch.length);
    }
  };
  for (const entry of entries) await walk(entry, "");
  return out;
}

// ---- uploading ----

function picked(event) {
  const list = [...event.target.files].map((file) => ({ file, path: file.webkitRelativePath || file.name }));
  event.target.value = "";
  upload(list, node.value);
}

function pickedVersion(event) {
  const file = event.target.files[0];
  event.target.value = "";
  const of = versionOf;
  versionOf = null;
  if (file && of) upload([{ file, path: file.name, version_of: of.id }], node.value);
}

async function upload(list, target) {
  if (!list.length) return;
  const rows = list.map((one) => reactive({ ...one, sent: 0, state: "waiting" }));
  uploads.value = uploads.value.filter((one) => one.state !== "done").concat(rows);
  for (let at = 0; at < rows.length; at += 200) {
    const batch = rows.slice(at, at + 200);
    let answer;
    try {
      answer = await call(UPLOAD + "begin", { node: target, files: batch.map((one) => ({ name: one.file.name, size: one.file.size, path: one.path })) });
    } catch (e) {
      batch.forEach((one) => (one.state = "failed"));
      continue;
    }
    const clashing = new Set(answer.existing || []);
    const clash = batch.filter((one) => !one.version_of && clashing.has(one.file.name));
    const replacing = clash.length ? await cloud().ask_replace(clash) : false;
    batch.forEach((one, i) => {
      one.node = target;
      one.ticket = answer.direct ? answer.tickets[i] : null;
      one.replace = replacing && clashing.has(one.file.name) ? 1 : 0;
    });
    await pool(batch, 3, send);
  }
  forget(target);
  if (target === node.value) refresh();
  else drawTree();
}

async function pool(list, most, work) {
  let next = 0;
  const lane = async () => {
    while (next < list.length) await work(list[next++]);
  };
  await Promise.all(Array.from({ length: Math.min(most, list.length) }, lane));
}

async function send(row) {
  row.state = "sending";
  try {
    if (row.ticket) {
      try {
        await xhr("PUT", row.ticket.url, row.file, row, { "Content-Type": row.ticket.type || row.file.type || "application/octet-stream" });
      } catch (e) {
        row.ticket = null;
      }
    }
    if (row.ticket) {
      await call(UPLOAD + "done", { token: row.ticket.token, path: row.path, replace: row.replace || 0, version_of: row.version_of || null });
    } else {
      const form = new FormData();
      form.append("node", row.node);
      form.append("path", row.path);
      form.append("replace", row.replace || 0);
      if (row.version_of) form.append("version_of", row.version_of);
      form.append("file", row.file, row.file.name);
      await xhr("POST", "/api/method/onedesk.one_storage.upload.here", form, row, { "X-Frappe-CSRF-Token": csrf(), Accept: "application/json" });
    }
    row.state = "done";
    row.sent = row.file.size;
  } catch (e) {
    row.state = "failed";
  }
}

function xhr(method, url, body, row, headers) {
  return new Promise((ok, no) => {
    const request = new XMLHttpRequest();
    request.open(method, url, true);
    Object.entries(headers || {}).forEach(([k, v]) => request.setRequestHeader(k, v));
    request.upload.onprogress = (event) => (row.sent = event.loaded);
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) return ok(request);
      let why = "";
      try {
        const answer = JSON.parse(request.responseText);
        why = answer._server_messages ? JSON.parse(JSON.parse(answer._server_messages)[0]).message : answer.exception || "";
      } catch (e) {
        why = "";
      }
      row.why = why;
      no(new Error(why || String(request.status)));
    };
    request.onerror = () => no(new Error("network"));
    request.send(body);
  });
}

// ---- the window, and starting ----

const searchBox = interfaceSearch(props.win, {
  placeholder: __("Search"),
  onInput: (value) => {
    search.value = value;
    refresh();
  },
  onKey: (event) => {
    if (event.key === "Escape") {
      setSearch("");
      refresh();
      list.value?.focus();
    }
    if (event.key === "ArrowDown") list.value?.focus();
  },
});
interfaceHandles(props.win, {
  kind: "files",
  up: () => act("up"),
  refresh: () => act("refresh"),
  path: (path) =>
    call(API + "resolve", { path })
      .then((found) => (go(found), true))
      .catch(() => false),
});
props.onTitle?.(__("OneCloud"));

watch(
  () => [here.value, newMenu.value, settings.view, search.value, treeRows.value],
  () =>
    interfaceHeading(props.win, {
      title: search.value ? __("Results for {0}", [search.value]) : here.value?.name || __("Files"),
      icon: search.value ? "lucide-search" : treeRows.value.find((one) => one.id === node.value)?.icon || "lucide-folder",
      primary: canNew.value
        ? {
            label: __("New"),
            menu: newMenu.value.flatMap((group) => group.options.filter((one) => !one.disabled).map((one) => ({ label: one.label, icon: one.icon, onclick: one.onClick }))),
          }
        : null,
      ways: views,
      ways_label: __("View"),
      way: settings.view,
      pick_way: (view) => remember({ view }),
    }),
  { flush: "post" }
);
onBeforeUnmount(() => interfaceHeading(props.win, null));
// Its frappe dialogs (share, members, servers, requests, drives) are desk's.
requires(onedesk().cloud_assets || []);

userSettings.get("File").then((kept) => {
  Object.assign(settings, (kept && kept.OneCloud) || {});
  ready = true;
  show();
});

function show() {
  if (!ready) return;
  const want = wanted();
  if (want === node.value) return refresh();
  if (!props.picker && !room) return open(want);
  open(want);
}

watch(
  () => [props.query.node, props.query.file],
  () => {
    if (props.picker || room) return;
    show();
  }
);

// A record's files dialog moves to another record's.
watch(
  () => props.room,
  (now) => {
    if (!now || now === room) return;
    room = now;
    past.value = [];
    ahead.value = [];
    setSearch("");
    if (ready) open(now);
  }
);

let soon = null;
const stop = listenIn("File", "onecloud_change", (data) => {
  const keys = (data && data.keys) || [];
  if (watching.value !== "*" && !keys.some((one) => (watching.value || []).includes(one))) return;
  clearTimeout(soon);
  soon = setTimeout(function again() {
    if (renaming.value || dragging.value) return (soon = setTimeout(again, 1500));
    forget(node.value);
    refresh();
    measure();
  }, 600);
});
onBeforeUnmount(() => {
  stop();
  clearTimeout(soon);
});
</script>
