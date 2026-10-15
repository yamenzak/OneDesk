<template>
  <!-- What the head says about the project beside its name, for its kind:
       status and health to change in place, then the kind's facts. How long
       is left is the Due card's, not said twice. Over a photo it is drawn
       in white. -->
  <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-base" :class="onImage ? 'text-white-overlay-900' : 'text-ink-gray-6'">
    <div class="flex items-center gap-2">
      <Pill :value="said.status" :options="['Open', 'On hold', 'Completed', 'Cancelled']" :colors="PROJECT_STATUS" :label="__('Status')" :readonly="!said.can_write" @change="(v) => $emit('change', 'status', v)" />
      <Pill v-if="said.status === 'Open'" :value="said.health" :options="['On Track', 'At Risk', 'Off Track']" :colors="HEALTH" :label="__('Health')" :empty="__('Set Health')" :readonly="!said.can_write" @change="(v) => $emit('change', 'one_health', v)" />
    </div>
    <button v-if="said.customer" class="flex items-center gap-1.5 hover:underline" @click="go(`/desk/customer/${said.customer}`)">
      <Avatar v-if="said.customer_image" :label="said.customer_name || said.customer" :image="said.customer_image" shape="square" size="xs" :class="onImage && 'bg-white-overlay-900'" />
      <span v-else class="lucide-building size-4" :class="icon" />{{ said.customer_name || said.customer }}
    </button>
    <button v-if="said.kind === 'Fixed Price' && said.orders?.length > 1" class="flex items-center gap-1.5 hover:underline" @click="go(said.orders_route)">
      <span class="lucide-file-signature size-4" :class="icon" />{{ __("{0} orders", [said.orders.length]) }}
    </button>
    <button v-else-if="said.kind === 'Fixed Price' && said.contract" class="flex items-center gap-1.5 hover:underline" @click="go(`/desk/sales-order/${said.contract}`)">
      <span class="lucide-file-signature size-4" :class="icon" />{{ said.contract }}
    </button>
    <template v-if="said.kind === 'Retainer'">
      <span v-if="said.starts" class="flex items-center gap-1.5"><span class="lucide-calendar size-4" :class="icon" />{{ __("Since {0}", [date(said.starts)]) }}</span>
      <span v-if="said.monthly_hours" class="flex items-center gap-1.5"><span class="lucide-timer size-4" :class="icon" />{{ __("{0} h a month", [said.monthly_hours]) }}</span>
    </template>
    <span v-else-if="dates" class="flex items-center gap-1.5"><span class="lucide-calendar size-4" :class="icon" />{{ dates }}</span>
    <span v-if="said.manager_name" class="flex items-center gap-1.5">
      <Avatar :label="said.manager_name" :image="said.manager_image" size="xs" />{{ said.manager_name }}
    </span>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Avatar } from "frappe-ui";

import { Pill, __, date, go } from "../kit";
import { HEALTH, PROJECT_STATUS } from "./colors";

const props = defineProps({ said: { type: Object, required: true }, onImage: Boolean });
defineEmits(["change"]);

const icon = computed(() => (props.onImage ? "text-white-overlay-700" : "text-ink-gray-5"));
const dates = computed(() => [props.said.starts, props.said.ends].filter(Boolean).map(date).join(" – "));
</script>
