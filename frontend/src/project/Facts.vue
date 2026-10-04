<template>
  <!-- What the head says about the project beside its name, for its kind:
       status and health to change in place, then the kind's facts. Over a
       photo it is drawn in white, and the team and progress are elsewhere. -->
  <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-base" :class="onImage ? 'text-white-overlay-900' : 'text-ink-gray-6'">
    <div class="flex items-center gap-2">
      <Pill :value="said.status" :options="['Open', 'Completed', 'Cancelled']" :colors="PROJECT_STATUS" :label="__('Status')" :readonly="!said.can_write" @change="(v) => $emit('change', 'status', v)" />
      <Pill :value="said.health" :options="['On Track', 'At Risk', 'Off Track']" :colors="HEALTH" :label="__('Health')" :empty="__('Set Health')" :readonly="!said.can_write" @change="(v) => $emit('change', 'one_health', v)" />
    </div>
    <button v-if="said.customer" class="flex items-center gap-1.5 hover:underline" @click="go(`/desk/customer/${said.customer}`)">
      <span class="lucide-building size-4" :class="icon" />{{ said.customer_name || said.customer }}
    </button>
    <button v-if="said.kind === 'Fixed Price' && said.contract" class="flex items-center gap-1.5 hover:underline" @click="go(`/desk/sales-order/${said.contract}`)">
      <span class="lucide-file-signature size-4" :class="icon" />{{ said.contract }}
    </button>
    <template v-if="said.kind === 'Retainer'">
      <span v-if="said.starts" class="flex items-center gap-1.5"><span class="lucide-calendar size-4" :class="icon" />{{ __("Since {0}", [date(said.starts)]) }}</span>
      <span v-if="said.monthly_hours" class="flex items-center gap-1.5"><span class="lucide-timer size-4" :class="icon" />{{ __("{0} h a month", [said.monthly_hours]) }}</span>
    </template>
    <span v-else-if="dates" class="flex items-center gap-1.5"><span class="lucide-calendar size-4" :class="icon" />{{ dates }}</span>
    <span v-if="said.kind === 'Internal' && due" class="flex items-center gap-1.5" :class="said.days_left < 0 && 'text-ink-red-5'"><span class="lucide-flag size-4" :class="said.days_left < 0 ? 'text-ink-red-5' : icon" />{{ due }}</span>
    <span v-if="said.manager_name" class="flex items-center gap-1.5">
      <Avatar :label="said.manager_name" size="xs" />{{ said.manager_name }}
    </span>
    <span v-if="!onImage && said.kind !== 'Retainer' && progress !== null" class="flex items-center gap-2 whitespace-nowrap">
      <div class="w-24"><Progress :value="progress" size="md" /></div>
      <span class="tabular-nums">{{ __("{0}% done", [progress]) }}</span>
    </span>
    <div v-if="!onImage" class="ms-auto">
      <People :users="said.team.map((one) => one.user)" :people="teamPeople" :max="6" size="md" />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Progress } from "frappe-ui";

import { People, Pill, __, date, go } from "../kit";
import { HEALTH, PROJECT_STATUS } from "./colors";

const props = defineProps({ said: { type: Object, required: true }, progress: { type: Number, default: null }, onImage: Boolean });
defineEmits(["change"]);

const icon = computed(() => (props.onImage ? "text-white-overlay-700" : "text-ink-gray-5"));
const dates = computed(() => [props.said.starts, props.said.ends].filter(Boolean).map(date).join(" – "));
const due = computed(() => {
  const left = props.said.days_left;
  if (left === null || left === undefined) return "";
  if (left < 0) return __("{0} days late", [-left]);
  return left === 0 ? __("Due today") : __("Due in {0} days", [left]);
});
const teamPeople = computed(() => Object.fromEntries(props.said.team.map((one) => [one.user, one])));
</script>
