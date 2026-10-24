<template>
  <div>
    <div class="flex flex-wrap gap-1.5">
      <Button size="sm" :label="said.explained || explained ? __('Explain Again') : __('Explain')" :loading="busy === 'explain'" :disabled="!!busy" @click="ask(false)" />
      <Button v-if="said.may_cancel" size="sm" :label="__('Write Cancellation')" :loading="busy === 'cancel'" :disabled="!!busy" @click="ask(true)" />
    </div>
    <div v-if="busy" class="mt-2 text-sm text-ink-gray-5">{{ busy === "cancel" ? __("Writing…") : __("Explaining…") }}</div>
    <div v-else-if="shown" class="mt-2 space-y-2 text-sm text-ink-gray-8">
      <p v-for="(one, at) in paragraphs" :key="at">{{ one }}</p>
      <template v-if="shown.todo?.length">
        <div class="text-xs font-medium text-ink-gray-5">{{ __("What to do") }}</div>
        <ul class="space-y-0.5">
          <li v-for="(one, at) in shown.todo" :key="at">{{ one.what }}<span v-if="one.by"> · {{ __("by {0}", [date(one.by)]) }}</span></li>
        </ul>
      </template>
      <template v-if="shown.reply">
        <div class="flex items-center gap-2 text-xs font-medium text-ink-gray-5">
          {{ __("Letter") }}
          <Button size="sm" variant="ghost" :label="__('Copy')" @click="copyText(shown.reply)" />
        </div>
        <pre class="whitespace-pre-wrap rounded-3 bg-surface-gray-1 p-2 font-sans text-sm">{{ shown.reply }}</pre>
      </template>
    </div>
  </div>
</template>

<script setup>
// OneAI explains a document in plain words, or writes the letter that
// cancels what it signs the reader up to (one_intake/explain.py).
import { computed, ref } from "vue";
import { Button } from "frappe-ui";

import { __, call, copyText, date } from "../kit";

const props = defineProps({ said: { type: Object, required: true } });

const explained = ref(null);
const busy = ref(null);
const shown = computed(() => explained.value || props.said.explained || null);
const paragraphs = computed(() => String(shown.value?.explanation || "").split(/\n\s*\n/).filter(Boolean));

async function ask(cancel) {
  busy.value = cancel ? "cancel" : "explain";
  try {
    explained.value = await call("onedesk.one_intake.explain.explain", {
      reading: props.said.name,
      cancel: cancel ? 1 : 0,
      again: !cancel && shown.value ? 1 : 0,
    });
  } catch (e) {
    explained.value = null;
  }
  busy.value = null;
}
</script>
