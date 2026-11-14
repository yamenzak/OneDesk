<template>
  <Dialog :open="!!file" :title="file ? file.file_name : ''" icon="lucide-paperclip" size="lg" :actions="actions" @update:open="(now) => !now && emit('close')">
    <div class="flex flex-col gap-3 text-base">
      <div v-if="busy" class="py-6 text-ink-gray-6"><LoadingText :text="__('Checking the file…')" /></div>
      <template v-else-if="said">
        <OneAlert :colour="COLOURS[said.state]">
          <p class="font-medium text-ink-gray-9">{{ HEADINGS[said.state] }}</p>
          <ul v-if="said.reasons.length" class="mt-1 list-disc space-y-0.5 ps-4 text-ink-gray-7">
            <li v-for="reason in said.reasons" :key="reason" class="break-words">{{ reason }}</li>
          </ul>
        </OneAlert>
        <div v-if="said.inside.length" class="flex flex-col">
          <div class="pb-1 text-sm text-ink-gray-5">{{ __("Files Inside") }}</div>
          <div class="max-h-60 overflow-auto">
            <div v-for="one in said.inside" :key="one.path" class="flex items-center gap-2 py-1 text-sm">
              <span :class="one.kind === 'program' ? 'lucide-octagon-alert text-ink-red-4' : 'lucide-file text-ink-gray-5'" class="size-3.5 shrink-0" aria-hidden="true" />
              <span class="min-w-0 flex-1 break-all text-ink-gray-8" dir="auto">{{ one.path }}</span>
              <span class="shrink-0 text-ink-gray-5">{{ fileSize(one.size) }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </Dialog>
</template>

<script setup>
// An attachment checked before it is opened (one_mail/sandbox.py, check):
// the clean copy first, the original second, a program never.
import { computed, ref, watch } from "vue";
import { Dialog, LoadingText } from "frappe-ui";

import { OneAlert, __, call, fileSize, openTab } from "../kit";

const props = defineProps({ message: { type: String, default: null }, file: { type: Object, default: null } });
const emit = defineEmits(["close"]);

const COLOURS = { never: "red", clean: "yellow", unchecked: "yellow", checked: "green" };
const HEADINGS = {
  never: __("This file can't be opened here"),
  clean: __("A clean copy was made"),
  unchecked: __("This file wasn't checked"),
  checked: __("Nothing risky was found"),
};

const said = ref(null);
const busy = ref(false);

watch(
  () => [props.message, props.file?.name],
  async ([message, file]) => {
    said.value = null;
    if (!message || !file) return;
    busy.value = true;
    try {
      const got = await call("onedesk.one_mail.sandbox.check", { message, file });
      if (file === props.file?.name) said.value = got;
    } finally {
      if (file === props.file?.name) busy.value = false;
    }
  },
  { immediate: true }
);

const opened = (address, close) => {
  openTab(address);
  close();
};
const cleanCopy = computed(() => `/api/method/onedesk.one_mail.sandbox.clean?${new URLSearchParams({ message: props.message || "", file: props.file?.name || "" })}`);
const actions = computed(() => {
  const now = said.value;
  if (busy.value || !now || !now.original) return [];
  const plain = now.state === "checked" && !now.reasons.length;
  const original = { label: plain ? __("Open") : __("Open Original"), variant: plain ? "solid" : "subtle", theme: plain ? "gray" : "red", onClick: ({ close }) => opened(now.original, close) };
  return now.clean ? [original, { label: __("Open Clean Copy"), variant: "solid", iconLeft: "lucide-shield-check", onClick: ({ close }) => opened(cleanCopy.value, close) }] : [original];
});
</script>
