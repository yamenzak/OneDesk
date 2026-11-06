<template>
  <div class="mx-auto w-full max-w-4xl px-5 pb-16 pt-6 text-ink-gray-8">
    <div class="rounded-4 border border-outline-gray-1 bg-surface-elevation-2 p-5">
      <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ left ? __("{0} of {1} ready", [count(ready.length), count(rows.length)]) : __("Everything is set up") }}</h2>
        <span v-if="shown" class="text-sm text-ink-gray-5">{{ shown }}</span>
        <span v-if="left" class="ms-auto text-sm text-ink-gray-5">{{ todo.length ? __("{0} to do", [count(todo.length)]) : __("Only suggestions left") }}</span>
      </div>
      <Progress :value="rows.length ? Math.round((100 * ready.length) / rows.length) : 0" size="md" class="mt-3" />
    </div>

    <section v-for="part in parts" :key="part.key" class="mt-6">
      <h3 class="mb-2 flex items-center gap-2 text-base font-semibold text-ink-gray-8">
        {{ part.title }}
        <span class="text-sm font-normal text-ink-gray-5">{{ count(part.rows.length) }}</span>
      </h3>
      <ul class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-1">
        <li v-for="one in part.rows" :key="one.check" class="flex items-start gap-3 px-4 py-3">
          <span :class="[part.icon, part.tone]" class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <div class="text-base font-medium" :class="part.key === 'ready' ? 'text-ink-gray-7' : 'text-ink-gray-9'">{{ one.check }}</div>
            <div class="mt-0.5 text-sm text-ink-gray-5">{{ one.says }}</div>
          </div>
          <Button v-if="one.fix" class="shrink-0" :variant="part.key === 'todo' ? 'solid' : 'subtle'" :label="__('Fix')" @click="onFix?.(one.fix)" />
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Button, Progress } from "frappe-ui";

import { __, company, count } from "../kit";

const props = defineProps({ rows: { type: Array, default: () => [] }, onFix: Function });

const shown = company();
const todo = computed(() => props.rows.filter((one) => one.state === "To Do"));
const suggested = computed(() => props.rows.filter((one) => one.state === "Suggested"));
const ready = computed(() => props.rows.filter((one) => one.state === "Ready"));
const left = computed(() => todo.value.length + suggested.value.length);

const parts = computed(() =>
  [
    { key: "todo", title: __("To Do"), rows: todo.value, icon: "lucide-circle-alert", tone: "text-ink-red-5" },
    { key: "suggested", title: __("Suggested"), rows: suggested.value, icon: "lucide-lightbulb", tone: "text-ink-amber-6" },
    { key: "ready", title: __("Ready"), rows: ready.value, icon: "lucide-circle-check", tone: "text-ink-green-4" },
  ].filter((part) => part.rows.length)
);
</script>
