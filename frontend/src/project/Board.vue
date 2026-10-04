<template>
  <!-- Tasks on a board by status: drag a card to another column to move it on. -->
  <div class="flex gap-3 overflow-x-auto pb-12 pt-4">
    <section
      v-for="status in columns"
      :key="status"
      class="flex w-72 shrink-0 flex-col rounded-5 bg-surface-gray-1 p-2"
      :class="over === status && 'ring-2 ring-outline-gray-3'"
      @dragover.prevent="over = status"
      @dragleave="over === status && (over = null)"
      @drop="drop(status)"
    >
      <div class="flex items-center gap-2 px-1.5 py-1">
        <span class="size-2 rounded-full" :class="SURFACE[TASK_STATUS[status] || 'gray']" />
        <span class="text-base font-medium text-ink-gray-8">{{ __(status) }}</span>
        <span class="text-base text-ink-gray-5">{{ byStatus[status].length }}</span>
      </div>
      <div class="mt-1 flex min-h-16 flex-col gap-2">
        <button
          v-for="task in byStatus[status]"
          :key="task.name"
          class="flex flex-col gap-2 rounded-4 border border-outline-gray-1 bg-surface-base p-3 text-start shadow-sm hover:border-outline-gray-3"
          :draggable="canWrite"
          @dragstart="dragging = task.name"
          @dragend="dragging = null"
          @click="$emit('open', task.name)"
        >
          <span class="text-base text-ink-gray-8">{{ task.subject }}</span>
          <span v-if="groupTitle(task)" class="truncate text-sm text-ink-gray-5">{{ groupTitle(task) }}</span>
          <span class="flex items-center gap-2">
            <Badge v-if="task.priority && task.priority !== 'Low'" :label="__(task.priority)" :theme="PRIORITY[task.priority]" size="sm" />
            <span v-if="task.exp_end_date" class="flex items-center gap-1 text-sm" :class="late(task) ? 'text-ink-red-5' : 'text-ink-gray-5'">
              <span class="lucide-calendar size-3.5" />{{ date(task.exp_end_date) }}
            </span>
            <span class="ms-auto"><People :users="task.assigned" :people="work.people" size="xs" /></span>
          </span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Badge } from "frappe-ui";

import { People, __, date, isPast } from "../kit";
import { DONE, PRIORITY, SURFACE, TASK_STATUS } from "./colors";

const props = defineProps({
  work: { type: Object, required: true },
  tasks: { type: Array, required: true },
  showDone: Boolean,
  canWrite: Boolean,
});
const emit = defineEmits(["open", "set"]);

const columns = computed(() => props.work.statuses.filter((one) => props.showDone || one !== "Cancelled"));
const byStatus = computed(() => Object.fromEntries(props.work.statuses.map((s) => [s, props.tasks.filter((t) => t.status === s)])));
const own = computed(() => props.work.groups[0]?.key);
const groupTitle = (task) => (task.project !== own.value ? props.work.groups.find((g) => g.key === task.project)?.title : "");
const late = (task) => !DONE.includes(task.status) && isPast(task.exp_end_date);

const dragging = ref(null);
const over = ref(null);
function drop(status) {
  over.value = null;
  const name = dragging.value;
  dragging.value = null;
  const task = props.tasks.find((one) => one.name === name);
  if (task && task.status !== status) emit("set", name, "status", status);
}
</script>
