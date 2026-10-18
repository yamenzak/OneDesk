<template>
  <div v-if="!steps.length" class="py-3 text-base text-ink-gray-5">{{ __("No operations here") }}</div>
  <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
    <div v-for="one in rows" :key="one.name" class="flex min-w-0 flex-col gap-3 rounded-4 border bg-surface-elevation-2 p-4" :class="one.running ? 'border-outline-green-2' : 'border-outline-gray-1'">
      <div class="flex min-w-0 items-start gap-2">
        <div class="min-w-0 flex-1">
          <button type="button" class="max-w-full truncate rounded-2 text-lg font-semibold text-ink-gray-9 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/job-card/${encodeURIComponent(one.name)}`)">{{ __(one.operation) }}</button>
          <button v-if="showOrder" type="button" class="block max-w-full truncate text-start text-sm text-ink-gray-5 hover:underline" @click="emit('open', one.work_order)">{{ __("{0} for {1}", [one.item_name || one.item, one.work_order]) }}</button>
          <div v-else-if="one.workstation" class="truncate text-sm text-ink-gray-5">{{ one.workstation }}</div>
        </div>
        <Badge :label="one.paused ? __('Paused') : __(one.status)" :theme="one.theme" size="md" />
      </div>

      <div class="flex items-center justify-between gap-3">
        <div class="flex min-w-0 items-center gap-2">
          <template v-if="one.people.length">
            <div class="flex -space-x-1.5">
              <Avatar v-for="who in one.people.slice(0, 3)" :key="who" :label="who" size="sm" :title="who" />
            </div>
            <span class="truncate text-sm text-ink-gray-6">{{ one.people.join(", ") }}</span>
          </template>
          <span v-else class="text-sm text-ink-gray-4">{{ __("Nobody on it yet") }}</span>
        </div>
        <span v-if="one.running || one.minutes" class="shrink-0 text-xl font-semibold tabular-nums" :class="one.running ? 'text-ink-green-4' : 'text-ink-gray-5'">{{ one.clock }}</span>
      </div>

      <div>
        <div class="mb-1.5 flex items-baseline justify-between text-sm tabular-nums text-ink-gray-6">
          <span>{{ __("{0} of {1} done", [quantity(one.done), quantity(one.for_quantity, one.uom)]) }}</span>
          <span v-if="one.loss" class="text-ink-gray-5">{{ __("{0} lost", [quantity(one.loss)]) }}</span>
        </div>
        <Progress :value="one.bar" size="md" />
      </div>

      <div v-for="(line, i) in one.lines" :key="i" class="flex items-start gap-1.5 text-sm" :class="line.tone === 'red' ? 'text-ink-red-5' : 'text-ink-gray-6'">
        <span :class="line.icon" class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        <span>{{ line.text }}</span>
      </div>
      <p v-if="one.instructions?.description" class="line-clamp-2 text-sm text-ink-gray-6">{{ one.instructions.description }}</p>

      <div class="mt-auto flex items-center gap-2 pt-1">
        <Button v-if="one.next" class="flex-1" size="md" :variant="one.next.solid ? 'solid' : 'subtle'" :label="one.next.label" :icon-left="one.next.icon" @click="one.next.onClick" />
        <span v-else class="flex-1" />
        <Dropdown v-if="one.more.length" :options="one.more" placement="right">
          <template #trigger><Button size="md" variant="subtle" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
        </Dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { Avatar, Badge, Button, Dropdown, Progress } from "frappe-ui";

import { __, duration, go, onedesk, quantity, secondsSince } from "../kit";

const props = defineProps({
  steps: { type: Array, required: true },
  can: { type: Object, required: true },
  employee: String,
  showOrder: Boolean,
});
const emit = defineEmits(["changed", "open"]);
const done = () => emit("changed");

const now = ref(Date.now());
const tick = setInterval(() => (now.value = Date.now()), 1000);
onBeforeUnmount(() => clearInterval(tick));

const THEMES = { "Work In Progress": "amber", "Material Transferred": "blue", "On Hold": "red", Completed: "green", "To Manufacture": "blue", Submitted: "green", "Not Started": "gray", Open: "gray" };

const rows = computed(() =>
  props.steps.map((one) => {
    now.value;
    const seconds = one.minutes * 60 + (one.running ? secondsSince(one.since) : 0);
    const bar = one.for_quantity ? Math.min(100, Math.round((100 * one.done) / one.for_quantity)) : 0;
    return {
      ...one,
      theme: one.paused ? "red" : THEMES[one.status] || "gray",
      clock: duration(seconds),
      bar,
      lines: [
        ...one.short.map((row) => ({ text: __("Short of {0}, {1} more needed", [row.item_name, quantity(row.shortage - row.on_hand_qty, row.uom)]), tone: "red", icon: "lucide-triangle-alert" })),
        one.qc.required && { text: one.qc.status ? __("Quality check {0}", [__(one.qc.status)]) : __("Needs a quality check before it closes"), tone: one.qc.status === "Rejected" ? "red" : null, icon: "lucide-shield-check" },
      ].filter(Boolean),
      next: next(one),
      more: more(one),
    };
  })
);

function next(one) {
  const may = one.may;
  if (may.finish && props.can["Stock Entry"]) return { label: __("Receive Into Stock"), icon: "lucide-package-check", solid: true, onClick: () => onedesk().floor.entry(one.name) };
  if (!props.can.start) return null;
  if (may.start) return { label: __("Start"), icon: "lucide-play", solid: true, onClick: () => onedesk().floor.start(one.name, props.employee, done) };
  if (may.pause) return { label: __("Pause"), icon: "lucide-pause", onClick: () => onedesk().floor.pause(one.name, done) };
  if (may.resume) return { label: __("Resume"), icon: "lucide-play", solid: true, onClick: () => onedesk().floor.resume(one.name, done) };
  if (may.submit && props.can.submit) return { label: __("Close Operation"), icon: "lucide-check", onClick: () => onedesk().floor.close(one, done) };
  return null;
}

function more(one) {
  const out = [];
  if (one.may.record && props.can.start) out.push({ label: __("Record Made"), icon: "lucide-clipboard-check", onClick: () => onedesk().floor.record(one, done) });
  if (one.to_move && one.docstatus === 0 && props.can["Stock Entry"]) out.push({ label: __("Transfer Material"), icon: "lucide-arrow-left-right", onClick: () => onedesk().floor.move(one.name) });
  if (one.instructions?.work_instruction) out.push({ label: __("Read Instructions"), icon: "lucide-book-open", onClick: () => onedesk().floor.instructions(one) });
  if (one.qc.has_checklist && one.docstatus === 0 && props.can["Quality Inspection"] && one.qc.status !== "Accepted") out.push({ label: __("Check Quality"), icon: "lucide-shield-check", onClick: () => onedesk().floor.check(one, done) });
  out.push({ label: __("Open Job Card"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/job-card/${encodeURIComponent(one.name)}`) });
  return out;
}
</script>
