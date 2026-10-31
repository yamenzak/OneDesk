<template>
  <div class="mx-auto flex w-full max-w-4xl flex-col gap-5 px-5 py-6">
    <Loading v-if="!desks" />
    <p v-else-if="!desks.length" class="text-base text-ink-gray-5">{{ __("No queues") }}</p>
    <template v-else>
      <div class="flex flex-wrap gap-2">
        <Select v-if="desks.length > 1" v-model="queue" class="w-48" :options="desks.map((one) => one.queue)" />
        <Select v-model="counter" class="w-40" :options="counters" :placeholder="__('Counter')" />
      </div>
      <Loading v-if="!state" />
      <div v-else class="grid gap-5 md:grid-cols-5">
        <section class="flex flex-col items-center gap-1 rounded-3 border border-outline-gray-2 p-6 text-center md:col-span-3">
          <p class="text-sm text-ink-gray-5">{{ __("Serving") }}</p>
          <p class="text-7xl font-bold tabular-nums text-ink-gray-9">{{ state.serving?.ticket || "—" }}</p>
          <p class="text-base text-ink-gray-5">{{ state.serving?.service || __("Nobody yet.") }}</p>
          <div class="mt-5 flex flex-wrap justify-center gap-2">
            <Button variant="solid" size="lg" :label="__('Call Next')" :loading="busy" @click="run('call_next', { queue, counter })" />
            <template v-if="state.serving">
              <Button size="lg" :label="__('Call Again')" @click="run('recall', { ticket: state.serving.name })" />
              <Button size="lg" :label="__('Done')" @click="run('finish', { ticket: state.serving.name, status: 'Done' })" />
              <Button size="lg" :label="__('No Show')" @click="run('finish', { ticket: state.serving.name, status: 'No Show' })" />
            </template>
          </div>
        </section>
        <section class="md:col-span-2">
          <h3 class="mb-1 text-sm font-medium text-ink-gray-5">{{ __("Waiting ({0})", [state.waiting.length]) }}</h3>
          <div v-for="one in state.waiting" :key="one.name" class="flex items-baseline gap-3 border-b border-outline-gray-1 py-2 last:border-0">
            <span class="w-14 text-base font-semibold tabular-nums text-ink-gray-9">{{ one.ticket }}</span>
            <span class="min-w-0 flex-1 truncate text-sm text-ink-gray-7">{{ one.service }}</span>
            <span class="text-sm text-ink-gray-5">{{ ago(one.creation) }}</span>
          </div>
          <p v-if="!state.waiting.length" class="py-2 text-sm text-ink-gray-5">{{ __("No one is waiting.") }}</p>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { Button, Select } from "frappe-ui";

import { Loading, __, ago, call } from "../kit";

const KEY = "one_display_counter";
const API = "onedesk.one_display.queue.";
const EVERY = 5000;

const desks = ref(null);
const queue = ref(null);
const counter = ref(null);
const state = ref(null);
const busy = ref(false);
let timer = null;

const desk = computed(() => desks.value?.find((one) => one.queue === queue.value));
const counters = computed(() => desk.value?.counters || []);

function remembered() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

async function load() {
  clearTimeout(timer);
  if (!queue.value || !counter.value) return;
  state.value = await call(API + "counter_state", { queue: queue.value, counter: counter.value });
  timer = setTimeout(load, EVERY);
}

async function run(method, args) {
  busy.value = true;
  try {
    state.value = await call(API + method, args);
  } finally {
    busy.value = false;
  }
  clearTimeout(timer);
  timer = setTimeout(load, EVERY);
}

watch(queue, () => {
  const saved = remembered();
  counter.value = counters.value.includes(saved.counter) ? saved.counter : desk.value?.mine || counters.value[0] || null;
});

watch(counter, () => {
  localStorage.setItem(KEY, JSON.stringify({ queue: queue.value, counter: counter.value }));
  state.value = null;
  load();
});

onMounted(async () => {
  desks.value = await call(API + "desks");
  const saved = remembered();
  queue.value = desks.value.find((one) => one.queue === saved.queue)?.queue || desks.value[0]?.queue || null;
});

onUnmounted(() => clearTimeout(timer));
</script>
