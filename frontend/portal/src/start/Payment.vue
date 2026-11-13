<template>
  <div class="flex flex-col gap-4">
    <dl v-if="!paying" class="flex flex-col gap-3 text-base">
      <div class="flex justify-between gap-4">
        <dt class="text-ink-gray-6">{{ __("Workspace") }}</dt>
        <dd class="text-end text-ink-gray-9">{{ answers.companies[0].name }}</dd>
      </div>
      <div class="flex justify-between gap-4">
        <dt class="text-ink-gray-6">{{ __("Address") }}</dt>
        <dd class="text-end text-ink-gray-9">{{ `${held.slug}.${offer.domain}` }}</dd>
      </div>
      <div v-if="plan" class="flex justify-between gap-4">
        <dt class="text-ink-gray-6">{{ __("Plan") }}</dt>
        <dd class="text-end text-ink-gray-9">{{ `${plan.label} · ${plan.price}` }}</dd>
      </div>
    </dl>
    <div ref="into" />
    <template v-if="!paying">
      <Button variant="solid" size="lg" :label="__('Continue to Payment')" :loading="busy" @click="open" />
      <ErrorMessage :message="error" />
      <p class="text-p-sm text-ink-gray-5">{{ offer.pay_note }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button, ErrorMessage } from "frappe-ui";

import { __, boot } from "../words";
import { answers, held, offer, pay } from "./wizard";

const PAY = "/assets/onedesk/js/one_admin/one_pay.js";

const plan = computed(() => offer.value.plans.find((one) => one.name === held.plan));
const into = ref(null);
const busy = ref(false);
const paying = ref(false);
const error = ref("");

function script() {
  if (window.onePay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const tag = document.createElement("script");
    tag.src = PAY;
    tag.onload = resolve;
    tag.onerror = reject;
    document.head.appendChild(tag);
  });
}

async function open() {
  busy.value = true;
  error.value = "";
  try {
    const [said] = await Promise.all([pay(), script()]);
    paying.value = true;
    await window.onePay(into.value, said.checkout, { locale: boot().lang || "auto" });
  } catch (refused) {
    paying.value = false;
    error.value = refused?.messages?.[0] || __("That did not work. Try again in a moment.");
  } finally {
    busy.value = false;
  }
}

defineExpose({ ready: computed(() => false), own: true, said: () => ({}) });
</script>
