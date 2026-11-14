<template>
  <Button variant="ghost" icon-left="lucide-message-circle-question" :label="__('Ask', null, 'Ask a question')" :aria-label="__('Ask the Setup Guide')" @click="open = true" />
  <Dialog v-model:open="open" :title="__('Setup Guide')" icon="lucide-message-circle-question" size="lg">
    <template #default>
      <div ref="list" class="flex max-h-[55dvh] flex-col gap-3 overflow-y-auto">
        <p v-if="!said.length" class="text-p-base text-ink-gray-6">{{ __("Ask what a question means, what a plan includes or which apps suit your company.") }}</p>
        <div v-for="(one, at) in said" :key="at" :class="one.role === 'you' ? 'self-end' : 'self-start'" class="max-w-[85%]">
          <p :class="one.role === 'you' ? 'bg-surface-gray-2 text-ink-gray-9' : 'text-ink-gray-8'" class="whitespace-pre-line rounded-3 px-3 py-2 text-p-base" dir="auto">{{ one.text }}</p>
          <div v-for="tip in one.suggestions || []" :key="tip.question" class="mt-2 flex items-center gap-3 rounded-3 border border-outline-gray-2 px-3 py-2">
            <div class="min-w-0 flex-1">
              <p class="text-base font-medium text-ink-gray-9">{{ tip.shown }}</p>
              <p v-if="tip.why" class="mt-0.5 text-p-sm text-ink-gray-6" dir="auto">{{ tip.why }}</p>
            </div>
            <Button v-if="!tip.used" variant="subtle" :label="__('Use This')" :loading="tip.busy" @click="take(tip)" />
            <span v-else class="flex shrink-0 items-center gap-1 text-p-sm text-ink-green-3"><span class="lucide-check size-4" aria-hidden="true" />{{ __("Used") }}</span>
          </div>
        </div>
        <p v-if="busy" class="text-p-base text-ink-gray-5">{{ __("Thinking…") }}</p>
      </div>
      <ErrorMessage class="mt-3" :message="error" />
      <form class="mt-4 flex items-end gap-2" @submit.prevent="send">
        <Textarea v-model="text" class="flex-1" :rows="2" :placeholder="__('Ask a question')" :disabled="busy" @keydown.enter.exact.prevent="send" />
        <Button type="submit" variant="solid" icon="lucide-send" :aria-label="__('Send')" :loading="busy" :disabled="!text.trim()" />
      </form>
      <p class="mt-2 text-p-sm text-ink-gray-5">{{ __("Answers come from {0} and can be wrong. Nothing is chosen until you press Use This.", [ai]) }}</p>
    </template>
  </Dialog>
</template>

<script setup>
import { nextTick, ref } from "vue";
import { Button, Dialog, ErrorMessage, Textarea } from "frappe-ui";

import { __ } from "../words";
import { askGuide, offer, use } from "./wizard";

const props = defineProps({ step: { type: String, default: "" } });

const ai = offer.value?.names?.one_ai || "";
const open = ref(false);
const text = ref("");
const said = ref([]);
const busy = ref(false);
const error = ref("");
const list = ref(null);

const down = () => nextTick(() => list.value && (list.value.scrollTop = list.value.scrollHeight));

async function send() {
  const question = text.value.trim();
  if (!question || busy.value) return;
  const before = said.value.map((one) => ({ role: one.role === "you" ? "you" : "guide", text: one.text }));
  said.value.push({ role: "you", text: question });
  text.value = "";
  busy.value = true;
  error.value = "";
  down();
  try {
    const out = await askGuide(question, props.step, before);
    said.value.push({ role: "guide", text: out.answer || __("No answer came back. Ask again in other words."), suggestions: (out.suggestions || []).map((one) => ({ ...one, used: false, busy: false })) });
  } catch (refused) {
    error.value = refused?.messages?.[0] || __("That did not work. Try again in a moment.");
  } finally {
    busy.value = false;
    down();
  }
}

async function take(tip) {
  tip.busy = true;
  error.value = "";
  try {
    await use(tip);
    tip.used = true;
  } catch (refused) {
    error.value = refused?.messages?.[0] || __("That did not work. Try again in a moment.");
  } finally {
    tip.busy = false;
  }
}
</script>
