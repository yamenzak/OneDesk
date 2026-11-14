<template>
  <Dialog :open="!!message" :title="__('Preview Link')" size="xl" :actions="actions" @update:open="(now) => !now && emit('close')">
    <div class="flex flex-col gap-3 text-base">
      <div v-if="!url" class="flex flex-col">
        <button
          v-for="one in choices"
          :key="one.url"
          type="button"
          class="flex flex-col items-start rounded-3 px-2 py-1.5 text-start hover:bg-surface-gray-2"
          @click="picked = one.url"
        >
          <span class="max-w-full truncate text-ink-gray-8" dir="auto">{{ one.words || one.url }}</span>
          <span class="max-w-full break-all text-sm text-ink-gray-5" dir="ltr">{{ one.url }}</span>
        </button>
      </div>
      <div v-else class="min-w-0">
        <div class="text-ink-gray-5">{{ __("Opens") }}</div>
        <div class="break-all font-medium text-ink-gray-9" dir="ltr">{{ url }}</div>
      </div>
      <div v-if="busy" class="flex items-center gap-2 py-6 text-ink-gray-6"><LoadingText :text="__('Opening the page in a throwaway browser…')" /></div>
      <template v-else-if="seen">
        <OneAlert v-if="seen.asks_password" colour="red">
          <p class="font-medium text-ink-gray-9">{{ __("This page asks for a password.") }}</p>
          <p class="text-ink-gray-7">{{ __("Sign in only on a site you opened yourself.") }}</p>
        </OneAlert>
        <OneAlert v-if="seen.moved && seen.site" colour="yellow">{{ __("It ends at {0}, not where the link points.", [seen.site]) }}</OneAlert>
        <OneAlert v-if="seen.warning" :colour="seen.failed === 'download' ? 'red' : 'gray'">{{ seen.warning }}</OneAlert>
        <img
          v-if="seen.picture"
          :src="seen.picture"
          :alt="__('Picture of the page')"
          class="max-h-[50vh] w-full rounded-3 border border-outline-gray-2 object-cover object-top"
        />
        <div v-if="!seen.failed || seen.failed === 'slow'" class="flex flex-col gap-0.5 text-sm">
          <span v-if="seen.title" class="truncate text-ink-gray-8" dir="auto">{{ seen.title }}</span>
          <span class="break-all text-ink-gray-5" dir="ltr">{{ seen.final_url }}</span>
          <span v-if="seen.redirects" class="text-ink-gray-5">{{ seen.redirects === 1 ? __("Redirected once") : __("Redirected {0} times", [seen.redirects]) }}</span>
        </div>
        <p class="text-sm text-ink-gray-5">{{ __("Opened without your sign-in or cookies.") }}</p>
      </template>
    </div>
  </Dialog>
</template>

<script setup>
// A link of a message seen in a throwaway browser before it is opened
// (one_mail/sandbox.py, link).
import { computed, ref, watch } from "vue";
import { Dialog, LoadingText } from "frappe-ui";

import { OneAlert, __, call, openOutside } from "../kit";

const props = defineProps({ message: { type: String, default: null }, link: { type: String, default: null }, choices: { type: Array, default: () => [] } });
const emit = defineEmits(["close"]);

const seen = ref(null);
const busy = ref(false);
const picked = ref(null);
const url = computed(() => picked.value || props.link || (props.choices.length === 1 ? props.choices[0].url : null));
watch(
  () => [props.message, props.link],
  () => (picked.value = null)
);

watch(
  () => [props.message, url.value],
  async ([message, asked]) => {
    seen.value = null;
    if (!message || !asked) return;
    busy.value = true;
    try {
      const got = await call("onedesk.one_mail.sandbox.link", { message, url: asked });
      if (asked === url.value) seen.value = got;
    } finally {
      if (asked === url.value) busy.value = false;
    }
  },
  { immediate: true }
);

const risky = computed(() => !!(seen.value && (seen.value.asks_password || seen.value.moved || seen.value.failed === "download")));
const actions = computed(() =>
  busy.value || !seen.value || seen.value.failed === "unreachable"
    ? []
    : [
        {
          label: __("Open Link"),
          variant: risky.value ? "subtle" : "solid",
          theme: risky.value ? "red" : "gray",
          iconLeft: "lucide-external-link",
          onClick: ({ close }) => {
            openOutside(url.value);
            close();
          },
        },
      ]
);
</script>
