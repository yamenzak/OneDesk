<template>
  <!-- Everything attached to the project, its sub-projects and their tasks, in one place. -->
  <div class="pb-12 pt-4">
    <div class="mb-3 flex items-center gap-2">
      <span class="text-base text-ink-gray-5">{{ files?.length ? (files.length === 1 ? __("1 file") : __("{0} files", [files.length])) : "" }}</span>
      <Button class="ms-auto" icon-left="lucide-upload" :label="__('Upload')" @click="pick" />
    </div>
    <Loading v-if="!files" />
    <div v-else-if="!files.length" class="flex flex-col items-center gap-3 py-16 text-center">
      <span class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5"><span class="lucide-paperclip block size-6" /></span>
      <p class="text-base text-ink-gray-7">{{ __("No files") }}</p>
      <Button variant="solid" icon-left="lucide-upload" :label="__('Upload')" @click="pick" />
    </div>
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <a v-for="file in files" :key="file.name" :href="file.file_url" target="_blank" rel="noopener" class="flex items-center gap-3 rounded-5 border border-outline-gray-2 p-3 hover:border-outline-gray-3 hover:bg-surface-gray-1">
        <span class="flex size-10 shrink-0 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-6"><span :class="icon(file)" class="size-5" /></span>
        <span class="min-w-0">
          <span class="block truncate text-base text-ink-gray-8">{{ file.file_name }}</span>
          <span class="block truncate text-sm text-ink-gray-5">{{ where(file) }} · {{ ago(file.creation) }}</span>
        </span>
      </a>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { Loading, __, ago, call, follow, upload } from "../kit";

const props = defineProps({ project: { type: String, required: true }, work: Object });
const emit = defineEmits(["count"]);
const files = ref(null);

async function load() {
  files.value = await call("onedesk.one_project.view.files", { project: props.project });
  emit("count", files.value.length);
}
let stop = () => {};
watch(
  () => props.project,
  (now) => {
    stop();
    files.value = null;
    stop = follow("Project", now, load);
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop());

const pick = () => upload("Project", props.project, load);
const KINDS = { pdf: "lucide-file-text", png: "lucide-image", jpg: "lucide-image", jpeg: "lucide-image", webp: "lucide-image", xlsx: "lucide-sheet", csv: "lucide-sheet", docx: "lucide-file-text", zip: "lucide-file-archive" };
const icon = (file) => KINDS[(file.file_name.split(".").pop() || "").toLowerCase()] || "lucide-file";
const where = (file) => {
  if (file.attached_to_doctype === "Task") return props.work?.tasks.find((t) => t.name === file.attached_to_name)?.subject || file.attached_to_name;
  return props.work?.groups.find((g) => g.key === file.attached_to_name)?.title || file.attached_to_name;
};
</script>
