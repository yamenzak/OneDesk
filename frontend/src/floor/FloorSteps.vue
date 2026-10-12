<template>
  <!-- A work order's or a workstation's steps, each a job card: who is on
       it and for how long, how many are done of how many, what of its
       materials is short, what it says to do, its quality check, and the
       button for what comes next, as ERPNext's Shop Floor offers it. -->
  <div v-if="!steps.length" class="py-3 text-base text-ink-gray-5">{{ __("No steps here") }}</div>
  <ul v-else class="divide-y divide-outline-gray-1">
    <li v-for="one in rows" :key="one.name" class="flex flex-wrap gap-x-4 gap-y-2 py-3">
      <span class="mt-2 h-2 w-2 shrink-0 rounded-full" :class="one.running ? 'bg-surface-green-5' : one.late ? 'bg-surface-red-5' : 'bg-surface-gray-4'" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 flex-wrap items-center gap-2">
          <button type="button" class="truncate rounded-2 text-base font-medium text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/job-card/${encodeURIComponent(one.name)}`)">
            {{ __(one.operation) }}
          </button>
          <span v-if="one.workstation" class="text-base text-ink-gray-5">{{ one.workstation }}</span>
          <Badge :label="one.paused ? __('Paused') : __(one.status)" :theme="one.theme" size="sm" />
        </div>
        <button v-if="showOrder" type="button" class="text-sm text-ink-gray-5 hover:underline" @click="emit('open', one.work_order)">{{ __("{0} for {1}", [one.item, one.work_order]) }}</button>
        <div v-for="(line, i) in one.lines" :key="i" class="text-sm text-ink-gray-5" :class="line.tone === 'red' && 'text-ink-red-4'">{{ line.text }}</div>
        <p v-if="one.instructions?.description" class="mt-1 line-clamp-2 text-sm text-ink-gray-6">{{ one.instructions.description }}</p>
        <Progress v-if="one.partway" :value="one.bar" size="sm" class="mt-2 max-w-64" />
      </div>
      <div class="flex shrink-0 items-start gap-1">
        <span v-if="one.running || one.minutes" class="me-2 pt-1.5 text-base tabular-nums" :class="one.running ? 'text-ink-green-4' : 'text-ink-gray-5'">{{ one.clock }}</span>
        <Button v-if="one.next" :variant="one.next.solid ? 'solid' : 'subtle'" :label="one.next.label" :icon-left="one.next.icon" @click="one.next.onClick" />
        <Dropdown v-if="one.more.length" :options="one.more" placement="right">
          <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
        </Dropdown>
      </div>
    </li>
  </ul>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { Badge, Button, Dropdown, Progress } from "frappe-ui";

import { __, duration, go, onedesk, quantity, secondsSince } from "../kit";

const props = defineProps({
  steps: { type: Array, required: true },
  // What the reader may do (floor.read's `can`).
  can: { type: Object, required: true },
  // The reader's own employee, who a start puts on the step.
  employee: String,
  // Each step says which work order it is for, on a workstation's tab.
  showOrder: Boolean,
});
const emit = defineEmits(["changed", "open"]);
const done = () => emit("changed");

// A clock for the steps someone is on, ticking while one is.
const now = ref(Date.now());
const tick = setInterval(() => (now.value = Date.now()), 1000);
onBeforeUnmount(() => clearInterval(tick));

const THEMES = { "Work In Progress": "orange", "Material Transferred": "blue", "On Hold": "red", Completed: "green", "To Manufacture": "blue", Submitted: "green", "Not Started": "gray", Open: "gray" };

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
      // A bar only while it is part done, the badge says the rest.
      partway: bar > 0 && bar < 100,
      lines: [
        { text: [__("{0} of {1} done", [quantity(one.done), quantity(one.for_quantity, one.uom)]), one.loss && __("{0} lost", [quantity(one.loss)])].filter(Boolean).join(" · ") },
        one.people.length && { text: one.people.join(", ") },
        ...one.short.map((row) => ({ text: __("Short of {0}, {1} more needed", [row.item_name, quantity(row.shortage - row.on_hand_qty, row.uom)]), tone: "red" })),
        one.qc.required && { text: one.qc.status ? __("Quality check {0}", [__(one.qc.status)]) : __("Needs a quality check before it closes"), tone: one.qc.status === "Rejected" ? "red" : null },
      ].filter(Boolean),
      next: next(one),
      more: more(one),
    };
  })
);

// The one thing to do next on a step, as a button.
function next(one) {
  const may = one.may;
  if (may.finish && props.can["Stock Entry"]) return { label: __("Receive Into Stock"), icon: "lucide-package-check", solid: true, onClick: () => onedesk().floor.entry(one.name) };
  if (!props.can.start) return null;
  if (may.start) return { label: __("Start"), icon: "lucide-play", solid: true, onClick: () => onedesk().floor.start(one.name, props.employee, done) };
  if (may.pause) return { label: __("Pause"), icon: "lucide-pause", onClick: () => onedesk().floor.pause(one.name, done) };
  if (may.resume) return { label: __("Resume"), icon: "lucide-play", solid: true, onClick: () => onedesk().floor.resume(one.name, done) };
  if (may.submit && props.can.submit) return { label: __("Close Step"), icon: "lucide-check", onClick: () => onedesk().floor.close(one, done) };
  return null;
}

// The rest, in the step's menu.
function more(one) {
  const out = [];
  if (one.may.record && props.can.start) out.push({ label: __("Record Made"), icon: "lucide-clipboard-check", onClick: () => onedesk().floor.record(one, done) });
  if (one.to_move && one.docstatus === 0 && props.can["Stock Entry"]) out.push({ label: __("Move Materials"), icon: "lucide-arrow-left-right", onClick: () => onedesk().floor.move(one.name) });
  if (one.instructions?.work_instruction) out.push({ label: __("Read Instructions"), icon: "lucide-book-open", onClick: () => onedesk().floor.instructions(one) });
  if (one.qc.has_checklist && one.docstatus === 0 && props.can["Quality Inspection"] && one.qc.status !== "Accepted") out.push({ label: __("Check Quality"), icon: "lucide-shield-check", onClick: () => onedesk().floor.check(one, done) });
  out.push({ label: __("Open Job Card"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/job-card/${encodeURIComponent(one.name)}`) });
  return out;
}
</script>
