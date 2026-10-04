<template>
  <!-- A due date: red once it has passed and the work is not done; clicking
       it picks another. -->
  <DatePicker
    v-if="!readonly"
    :model-value="value || ''"
    variant="ghost"
    :format="dateFormat()"
    :placeholder="__('Set Date')"
    :class="late ? '[&_input]:text-ink-red-5' : ''"
    @update:model-value="(v) => v !== value && $emit('change', v || null)"
  />
  <span v-else class="text-base" :class="late ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ date(value) }}</span>
</template>

<script setup>
import { computed } from "vue";
import { DatePicker } from "frappe-ui";

import { __, date, dateFormat, isPast } from "../kit";

const props = defineProps({ value: String, done: Boolean, readonly: Boolean });
defineEmits(["change"]);
const late = computed(() => !props.done && isPast(props.value));
</script>
