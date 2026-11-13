<template>
  <div class="flex flex-col">
    <div v-for="one in offer.apps" :key="one.id" class="flex items-start gap-3 py-3">
      <img v-if="one.mark" :src="one.mark" alt="" class="size-9 shrink-0" />
      <div class="min-w-0 flex-1">
        <p class="text-base font-medium text-ink-gray-9">{{ one.name }}</p>
        <p v-if="one.line" class="mt-0.5 text-p-sm text-ink-gray-6">{{ one.line }}</p>
        <p v-if="said(one)" class="mt-1 text-p-sm text-ink-gray-5">{{ said(one) }}</p>
      </div>
      <Switch :model-value="on(one)" :disabled="one.always || Boolean(held.needed_by[one.id]) || busy" :aria-label="one.name" @update:model-value="(yes) => turn(one, yes)" />
    </div>
    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ErrorMessage, Switch } from "frappe-ui";

import { __ } from "../words";
import { answers, held, offer, save } from "./wizard";

const busy = ref(false);
const error = ref("");

const on = (one) => one.always || Boolean(answers.apps[one.id]);

function said(one) {
  if (one.always) return one.kept;
  const by = held.needed_by[one.id];
  if (by) return __("On because {0} needs it.", [by.join(", ")]);
  if (one.kept && on(one)) return `${one.kept} ${__("Can't be turned off once it holds records.")}`;
  return "";
}

async function turn(one, yes) {
  answers.apps = { ...answers.apps, [one.id]: yes };
  busy.value = true;
  error.value = "";
  try {
    await save("apps", { answers: { apps: answers.apps } });
  } catch (refused) {
    error.value = refused?.messages?.[0] || __("That did not work. Try again in a moment.");
  } finally {
    busy.value = false;
  }
}

const ready = computed(() => !busy.value);

defineExpose({ ready, said: () => ({ answers: { apps: answers.apps } }) });
</script>
