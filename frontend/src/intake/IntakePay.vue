<template>
  <div>
    <div class="mb-1 text-xs font-medium text-ink-gray-5">{{ __("Payment") }}</div>
    <OneAlert v-if="pay.warn" :text="pay.warn" colour="red" />
    <div v-else class="flex flex-wrap items-start gap-3">
      <dl class="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1 text-sm">
        <template v-for="row in rows" :key="row.label">
          <dt class="text-ink-gray-5">{{ row.label }}</dt>
          <dd>
            <button type="button" class="rounded-2 px-1 text-start hover:bg-surface-gray-2" :title="__('Copy')" @click="copyText(String(row.value))">
              {{ row.shown }}
            </button>
          </dd>
        </template>
      </dl>
      <div v-if="pay.code" class="size-28 shrink-0" :title="__('Scan with your banking app')" v-html="pay.code" />
    </div>
  </div>
</template>

<script setup>
// How to pay a bill OneAI read, each line copied with a click, and the code a
// banking app scans.
import { computed } from "vue";

import { OneAlert, __, copyText, money } from "../kit";

const props = defineProps({ pay: { type: Object, required: true } });

const rows = computed(() => {
  const pay = props.pay;
  return [
    { label: __("To"), value: pay.name, shown: pay.name },
    { label: __("IBAN"), value: pay.iban, shown: String(pay.iban || "").replace(/(.{4})/g, "$1 ").trim() },
    { label: __("Amount"), value: pay.amount, shown: pay.amount ? money(pay.amount, pay.currency) : "" },
    { label: __("Reference"), value: pay.reference, shown: pay.reference },
  ].filter((row) => row.value);
});
</script>
