<template>
  <div class="flex flex-col gap-5">
    <div class="grid grid-cols-2 gap-3">
      <FormControl v-model="day.starts" type="time" size="lg" :label="__('Starts')" required />
      <FormControl v-model="day.ends" type="time" size="lg" :label="__('Ends')" required />
    </div>
    <div class="flex flex-col gap-2">
      <p class="text-sm text-ink-gray-6">{{ __("Days Off") }}</p>
      <div class="flex flex-wrap gap-2">
        <Button
          v-for="one in WEEK"
          :key="one"
          :variant="day.days_off.includes(one) ? 'solid' : 'subtle'"
          :label="__(one)"
          :aria-pressed="day.days_off.includes(one)"
          @click="flip(one)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from "vue";
import { Button, FormControl } from "frappe-ui";

import { answers, offer } from "./wizard";

const WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const held = answers.working_day || {};
const day = reactive({
  starts: held.starts || offer.value.day[0],
  ends: held.ends || offer.value.day[1],
  days_off: [...(held.days_off || offer.value.weekend[answers.companies[0].country] || offer.value.weekend_elsewhere)],
});

const flip = (one) => (day.days_off = day.days_off.includes(one) ? day.days_off.filter((other) => other !== one) : [...day.days_off, one]);

const ready = computed(() => Boolean(day.starts && day.ends && day.starts < day.ends && day.days_off.length < WEEK.length));

defineExpose({ ready, said: () => ({ answers: { working_day: { starts: day.starts.slice(0, 5), ends: day.ends.slice(0, 5), days_off: WEEK.filter((one) => day.days_off.includes(one)) } } }) });
</script>
