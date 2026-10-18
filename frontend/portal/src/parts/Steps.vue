<template>
  <ol class="flex items-start">
    <li v-for="(step, i) in steps" :key="step.label" class="flex min-w-0 flex-1 flex-col items-center gap-2 text-center">
      <div class="flex w-full items-center">
        <span :class="['h-px flex-1', i === 0 ? 'opacity-0' : steps[i - 1].done && step.done ? 'bg-surface-gray-10' : 'bg-surface-gray-3']" />
        <span
          :class="[
            'grid size-6 shrink-0 place-items-center rounded-full border',
            step.done ? 'border-transparent bg-surface-gray-10 text-ink-base' : step.current ? 'border-outline-gray-5 bg-surface-base' : 'border-outline-gray-2 bg-surface-base',
          ]"
        >
          <span v-if="step.done" class="lucide-check size-3.5" aria-hidden="true" />
          <span v-else-if="step.current" class="size-2 rounded-full bg-surface-gray-10" />
        </span>
        <span :class="['h-px flex-1', i === steps.length - 1 ? 'opacity-0' : step.done && steps[i + 1].done ? 'bg-surface-gray-10' : 'bg-surface-gray-3']" />
      </div>
      <span :class="['px-1 text-sm', step.done || step.current ? 'font-medium text-ink-gray-8' : 'text-ink-gray-5']">{{ step.label }}</span>
    </li>
  </ol>
</template>

<script setup>
defineProps({ steps: { type: Array, required: true } });
</script>
