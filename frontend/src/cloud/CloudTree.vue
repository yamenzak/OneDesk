<template>
  <div role="tree" :aria-label="__('Folders')" class="py-1 text-base">
    <template v-for="row in rows" :key="row.node.id">
      <a
        :href="`/desk/onecloud?node=${encodeURIComponent(row.node.id)}`"
        role="treeitem"
        :aria-expanded="row.leaf ? undefined : row.open"
        :aria-current="row.node.id === here ? 'page' : undefined"
        :data-node="row.node.id"
        class="flex items-center gap-1.5 rounded-3 py-1.5 pe-2"
        :class="[
          row.node.id === here ? 'bg-surface-gray-3 font-medium text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2',
          dropOn === row.node.id ? 'ring-2 ring-outline-blue-5' : '',
          INDENT[Math.min(row.depth, INDENT.length - 1)],
        ]"
        @click.prevent="emit('go', row.node.id)"
        @dragover="emit('dragover', $event, row.node.id)"
        @dragleave="emit('dragleave', $event, row.node.id)"
        @drop="emit('drop', $event, row.node.id)"
      >
        <button
          type="button"
          class="flex size-4 shrink-0 items-center justify-center rounded-1 text-ink-gray-5 hover:bg-surface-gray-3"
          :disabled="row.leaf"
          :aria-label="row.open ? __('Collapse') : __('Expand')"
          @click.prevent.stop="emit('twist', row.node.id)"
        >
          <span v-if="!row.leaf" :class="row.open ? 'lucide-chevron-down' : 'lucide-chevron-right'" class="size-3.5" aria-hidden="true" />
        </button>
        <span :class="iconOf(row.node)" class="size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
        <span class="min-w-0 flex-1 truncate">{{ row.node.name }}</span>
      </a>
    </template>
  </div>
</template>

<script setup>
// OneCloud's folders as a tree: the places at the top (My Files, Company,
// Libraries, Records, the Recycle Bin), each folder opened as far as the
// reader opened it.
import { computed } from "vue";

import { __ } from "../kit";
import { iconOf } from "./cloud";

const props = defineProps({
  kids: { type: Object, required: true },
  open: { type: Set, required: true },
  here: { type: String, default: "" },
  dropOn: { type: String, default: null },
});
const emit = defineEmits(["go", "twist", "dragover", "dragleave", "drop"]);

const INDENT = ["ps-1", "ps-5", "ps-9", "ps-12", "ps-16", "ps-20", "ps-24"];

const rows = computed(() => {
  const out = [];
  const walk = (list, depth) => {
    for (const node of list || []) {
      const leaf = node.id === "@bin" || (node.record && !node.doctype);
      const open = props.open.has(node.id);
      out.push({ node, depth, leaf, open });
      if (open && props.kids[node.id]) walk(props.kids[node.id], depth + 1);
    }
  };
  walk(props.kids["@root"], 0);
  return out;
});
</script>
