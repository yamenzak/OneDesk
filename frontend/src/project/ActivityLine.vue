<template>
  <div class="flex flex-1 flex-col gap-1.5 ps-[13px] text-sm font-medium leading-6 text-ink-gray-5">
    <div class="flex items-start gap-1.5">
      <span class="min-w-0 break-words">
        <template v-if="activity.author?.fullname"><span class="text-ink-gray-8">{{ activity.author.fullname }}</span>{{ " " }}</template>
        <slot />
        <span v-if="aside" class="text-ink-gray-5"> · {{ aside }}</span>
      </span>
      <Tooltip :text="when">
        <span class="ms-auto whitespace-nowrap text-ink-gray-5">{{ ago(activity.timestamp) }}</span>
      </Tooltip>
    </div>
    <slot name="below" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Tooltip } from "frappe-ui";

import { ago, date } from "../kit";

const props = defineProps({ activity: { type: Object, required: true }, aside: String });
const when = computed(() => [date(props.activity.timestamp.slice(0, 10)), props.activity.timestamp.slice(11, 16)].join(" "));
</script>
