<template>
  <div class="p-4 text-sm text-ink-gray-8">
    <div v-if="chosen.length > 1" class="flex flex-col items-center gap-2 py-12 text-ink-gray-5">
      <span class="lucide-files size-8" aria-hidden="true" />
      <span class="text-base">{{ __("{0} items selected", [chosen.length]) }}</span>
      <span v-if="bytes">{{ sizeText(bytes) }}</span>
    </div>

    <template v-else-if="item">
      <div class="flex min-h-32 items-center justify-center overflow-hidden rounded-4 bg-surface-gray-1">
        <img v-if="shows('image')" :src="item.url" alt="" class="max-h-64 max-w-full object-contain" />
        <video v-else-if="shows('video')" controls preload="metadata" :src="item.url" class="max-h-64 max-w-full" />
        <audio v-else-if="shows('audio')" controls preload="metadata" :src="item.url" class="w-full" />
        <iframe v-else-if="shows('frame')" :title="item.name" :src="item.url" sandbox="allow-same-origin" class="h-64 w-full [border:none]" />
        <span v-else :class="iconOf(item)" class="size-12 text-ink-gray-5" aria-hidden="true" />
      </div>
      <div class="mt-3 break-words text-base font-semibold text-ink-gray-9">{{ item.name }}</div>
      <PlaceSpot :said="placed" class="mt-2" />
      <IntakePanel v-if="filed(item) && !item.folder" :file="item.id" class="mt-3" />
      <dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <template v-for="row in facts" :key="row[0]">
          <dt class="text-ink-gray-5">{{ row[0] }}</dt>
          <dd class="break-words">{{ row[1] }}</dd>
        </template>
      </dl>
      <template v-if="history">
        <template v-if="history.versions.length">
          <div class="mt-4 text-xs font-medium text-ink-gray-5">{{ __("Versions") }}</div>
          <div class="mt-1 flex justify-between gap-2 py-1"><span>{{ __("Current") }}</span><span class="text-ink-gray-5">{{ sizeText(item.size) }}</span></div>
          <div v-for="one in history.versions" :key="one.name" class="flex flex-wrap items-center gap-x-2 py-1">
            <span class="min-w-0 flex-1">{{ __("Version {0}", [one.version]) }} · {{ one.by }} · {{ dateText(one.on) }}</span>
            <span class="text-ink-gray-5">{{ sizeText(one.size) }}</span>
            <a :href="one.url" target="_blank" rel="noopener" class="underline">{{ __("Open") }}</a>
            <button type="button" class="underline" @click="restore(one)">{{ __("Restore") }}</button>
          </div>
        </template>
        <div class="mt-4 text-xs font-medium text-ink-gray-5">{{ __("Activity") }}</div>
        <div v-for="(one, at) in history.done" :key="at" class="py-1">
          <span class="font-medium">{{ one.who }}</span> {{ one.what }}
          <div class="text-xs text-ink-gray-5">{{ dateText(one.when) }}</div>
        </div>
      </template>
    </template>

    <template v-else>
      <div class="flex min-h-32 items-center justify-center rounded-4 bg-surface-gray-1">
        <span class="lucide-folder size-12 text-ink-gray-5" aria-hidden="true" />
      </div>
      <div class="mt-3 text-base font-semibold text-ink-gray-9">{{ hereName }}</div>
      <dl class="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <template v-for="row in folderFacts" :key="row[0]">
          <dt class="text-ink-gray-5">{{ row[0] }}</dt>
          <dd class="break-words">{{ row[1] }}</dd>
        </template>
      </dl>
    </template>
  </div>
</template>

<script setup>
// What is chosen, beside the files: a picture of it, what OneAI read from
// it, its facts, versions and what was done to it; with nothing chosen, the
// folder itself: how much is in it and who it is shared with.
import { computed, reactive, ref, watch } from "vue";

import { PlaceSpot, __, call, intakeOn, onedesk, userInfo } from "../kit";
import IntakePanel from "../intake/IntakePanel.vue";
import { PREVIEW, dateText, extension, filed, iconOf, sizeText, typeOf } from "./cloud";

const props = defineProps({
  chosen: { type: Array, default: () => [] },
  items: { type: Array, default: () => [] },
  node: { type: String, default: "" },
  hereName: { type: String, default: "" },
  picker: Boolean,
});
const emit = defineEmits(["changed"]);

const item = computed(() => (props.chosen.length === 1 ? props.chosen[0] : null));
const bytes = computed(() => props.chosen.reduce((sum, one) => sum + (one.folder ? 0 : one.size || 0), 0));
const history = ref(null);
const people = ref(null);
const reading = ref(null);
const placed = reactive({ notes: [], actions: [] });

const shows = (kind) => !item.value.folder && item.value.url && PREVIEW[kind].includes(extension(item.value));

const facts = computed(() => {
  const one = item.value;
  return [
    [__("Type"), typeOf(one)],
    [__("Size"), one.folder ? "" : sizeText(one.size)],
    [__("Modified"), dateText(one.modified)],
    [__("Deleted"), dateText(one.deleted)],
    [String(one.id).startsWith("@request/") ? __("Progress") : __("Folder"), one.where],
    [__("Owner"), one.owner ? userInfo(one.owner).name : ""],
    [__("Record"), one.record ? `${__(one.record[0])} ${one.record[1]}` : ""],
  ].filter(([, value]) => value);
});

const folderFacts = computed(() => {
  const files = props.items.filter((one) => !one.folder);
  const folders = props.items.length - files.length;
  const size = files.reduce((sum, one) => sum + (one.size || 0), 0);
  const rows = [
    [__("Folders"), folders ? String(folders) : ""],
    [__("Files"), files.length ? String(files.length) : ""],
    [__("Size"), size ? sizeText(size) : ""],
  ];
  if (people.value) {
    const seen = [...people.value.people, ...people.value.inherited];
    rows.push([__("Owner"), people.value.owner.name]);
    rows.push([__("Shared with"), seen.length ? seen.map((one) => one.name).join(", ") : __("No one else")]);
  }
  if (reading.value) rows.push([__("Read by OneAI"), reading.value.on ? __("Yes") : __("No")]);
  return rows.filter(([, value]) => value);
});

watch(
  item,
  async (one) => {
    history.value = null;
    tell(one);
    if (!one || !filed(one)) return;
    try {
      const found = await call("onedesk.one_storage.history.activity", { node: one.id });
      if (item.value?.id === one.id) history.value = found;
    } catch (e) {
      history.value = null;
    }
  },
  { immediate: true }
);

watch(
  () => props.node,
  async (node) => {
    people.value = null;
    reading.value = null;
    if (!node || node.startsWith("@")) return;
    const [who, read] = await Promise.all([
      call("onedesk.one_storage.share.people", { node }).catch(() => null),
      intakeOn() ? call("onedesk.one_intake.switches.folder_state", { folder: node }).catch(() => null) : null,
    ]);
    if (props.node !== node) return;
    people.value = who;
    reading.value = read;
  },
  { immediate: true }
);

async function restore(version) {
  await call("onedesk.one_storage.history.restore", { node: item.value.id, version: version.name });
  emit("changed");
}

// The file chosen, for whatever else listens on this place
// (onedesk.places, "onecloud.file").
function tell(one) {
  placed.notes = [];
  placed.actions = [];
  const places = onedesk().places;
  if (!one || one.folder || props.picker || !places?.listening("onecloud.file")) return;
  places.emit(
    "onecloud.file",
    {
      name: one.name,
      type: typeOf(one),
      size: one.size || 0,
      modified: one.modified || null,
      folder: one.where || "",
      owner: one.owner || "",
      record: one.record || null,
    },
    {
      note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
      action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
    }
  );
}
</script>
