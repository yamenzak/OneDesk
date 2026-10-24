<template>
  <div v-if="rows.length" class="w-80 overflow-hidden rounded-4 border border-outline-gray-2 bg-surface-elevation-2 text-sm">
    <div class="flex items-center gap-2 border-b border-outline-gray-1 px-3 py-2">
      <span class="flex-1 font-medium text-ink-gray-8">{{ title }}</span>
      <Button size="sm" variant="ghost" icon="lucide-x" :aria-label="__('Close')" :disabled="busy" @click="emit('close')" />
    </div>
    <div class="max-h-60 overflow-auto">
      <div v-for="(one, at) in rows.slice(-50)" :key="at" class="flex items-center gap-2 px-3 py-1.5" :title="one.why || ''">
        <span class="min-w-0 flex-1 truncate text-ink-gray-7">{{ one.path || one.file.name }}</span>
        <span class="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-surface-gray-3">
          <span class="block h-full bg-surface-blue-6" :class="BARS[Math.min(12, Math.round((12 * (one.sent || 0)) / (one.file.size || 1)))]" />
        </span>
        <span class="w-12 shrink-0 text-end text-xs" :class="one.state === 'failed' ? 'text-ink-red-6' : 'text-ink-gray-5'">
          {{ one.state === "failed" ? __("Failed") : one.state === "done" ? __("Done") : "" }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
// What is being uploaded, file by file, and how far each has gone.
import { computed } from "vue";
import { Button } from "frappe-ui";

import { __ } from "../kit";

const props = defineProps({ rows: { type: Array, default: () => [] } });
const emit = defineEmits(["close"]);

const BARS = ["w-0", "w-1/12", "w-2/12", "w-3/12", "w-4/12", "w-5/12", "w-6/12", "w-7/12", "w-8/12", "w-9/12", "w-10/12", "w-11/12", "w-full"];

const done = computed(() => props.rows.filter((one) => one.state === "done").length);
const failed = computed(() => props.rows.filter((one) => one.state === "failed").length);
const busy = computed(() => props.rows.some((one) => one.state === "waiting" || one.state === "sending"));
const title = computed(() => {
  const all = props.rows.length;
  if (busy.value) return __("Uploading {0} of {1}", [Math.min(done.value + failed.value + 1, all), all]);
  return failed.value ? __("{0} uploaded, {1} failed", [done.value, failed.value]) : __("{0} uploaded", [done.value]);
});
</script>
