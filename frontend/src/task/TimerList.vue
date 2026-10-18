<template>
  <div class="flex flex-col gap-4">
    <Loading v-if="!said" />
    <template v-else>
      <section v-if="said.running" class="rounded-3 border border-outline-gray-2 p-3">
        <div class="flex items-center gap-1.5 text-sm text-ink-gray-5">
          <span class="size-2 shrink-0 rounded-full bg-surface-green-7" aria-hidden="true" />
          {{ __("Running") }}
        </div>
        <button class="mt-1 block w-full truncate text-start text-base font-medium text-ink-gray-9 hover:underline" @click="open(said.running)">
          {{ said.running.subject }}
        </button>
        <p v-if="said.running.place" class="truncate text-sm text-ink-gray-5">{{ said.running.place.label }}</p>
        <p class="mt-3 text-2xl font-semibold tabular-nums text-ink-gray-9" :aria-label="__('Today on this task')">{{ duration(elapsed) }}</p>
        <div class="mt-3 flex gap-2">
          <Button :label="__('Pause Timer')" icon-left="lucide-pause" @click="pause" />
          <Button :label="__('Stop Timer')" icon-left="lucide-square" @click="stop(said.running)" />
        </div>
      </section>
      <section v-if="said.paused.length">
        <h3 class="mb-1 text-sm font-medium text-ink-gray-5">{{ __("Paused") }}</h3>
        <div v-for="one in said.paused" :key="one.task" class="flex items-center gap-1 border-b border-outline-gray-1 py-2 last:border-0">
          <div class="min-w-0 flex-1">
            <button class="block w-full truncate text-start text-base text-ink-gray-8 hover:underline" @click="open(one)">{{ one.subject }}</button>
            <p class="truncate text-sm text-ink-gray-5">{{ line(one) }}</p>
          </div>
          <Button variant="ghost" icon="lucide-play" :aria-label="__('Resume Timer')" :title="__('Resume Timer')" @click="resume(one)" />
          <Button variant="ghost" icon="lucide-square" :aria-label="__('Stop Timer')" :title="__('Stop Timer')" @click="stop(one)" />
        </div>
      </section>
      <div v-if="!said.running && !said.paused.length" class="flex flex-col items-center gap-1 py-6 text-center">
        <span class="lucide-timer size-6 text-ink-gray-4" aria-hidden="true" />
        <p class="mt-1 text-base text-ink-gray-7">{{ __("No timer running") }}</p>
        <p class="max-w-56 text-sm text-ink-gray-5">{{ __("Start one from a task with its play button. It keeps running when you leave the page.") }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { Button } from "frappe-ui";

import { Loading, __, call, duration, go, listen, onedesk, secondsSince } from "../kit";

const emit = defineEmits(["opened"]);

const said = ref(null);
const tick = ref(0);

async function load() {
  said.value = await call("onedesk.one_task.timer.timers");
}

const elapsed = computed(() => {
  tick.value;
  const now = said.value?.running;
  return now ? (now.today || 0) * 3600 + secondsSince(now.since) : 0;
});

const line = (one) =>
  [one.place?.label, one.today ? __("{0} today", [duration(one.today * 3600, { seconds: false })]) : ""].filter(Boolean).join(" · ");

const open = (one) => {
  emit("opened");
  go(`/desk/task/${encodeURIComponent(one.task)}`);
};

async function pause() {
  await call("onedesk.one_task.timer.pause");
  await load();
}

async function resume(one) {
  await call("onedesk.one_task.timer.start", { task: one.task });
  await load();
}

async function stop(one) {
  const hours = await call("onedesk.one_task.timer.stop", { task: one.task });
  if (said.value?.running?.task === one.task) onedesk().task_timer?.stopped?.(hours);
  await load();
}

let stopListening = () => {};
let clock = null;
onMounted(() => {
  load();
  stopListening = listen("one_timers", load);
  clock = setInterval(() => (tick.value += 1), 1000);
});
onUnmounted(() => {
  stopListening();
  clearInterval(clock);
});
</script>
