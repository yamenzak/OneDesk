<template>
  <Page data-tour="one-hub">
    <div class="mt-6">
      <TextInput v-model="search" class="w-full sm:max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')" data-tour="one-hub-search">
        <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
      </TextInput>
    </div>
    <p v-if="!shown.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing matches. Try fewer words.") }}</p>
    <div v-else class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" data-tour="one-hub-tiles">
      <button
        v-for="one in shown"
        :key="one.key"
        type="button"
        class="flex items-start gap-3 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3 text-start hover:bg-surface-gray-2"
        @click="open(one)"
      >
        <span class="flex size-9 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-7"><Mark :name="one.icon" class="icon size-5" /></span>
        <span class="flex min-w-0 flex-col gap-0.5">
          <span class="text-base font-medium text-ink-gray-8">{{ one.name }}</span>
          <span class="text-sm text-ink-gray-5">{{ one.line }}</span>
        </span>
      </button>
    </div>
  </Page>
</template>

<script setup>
import { computed, ref } from "vue";
import { TextInput } from "frappe-ui";

import { Mark, Page, __, name, onedesk } from "../kit";

const props = defineProps({ onTitle: Function });

props.onTitle?.({ title: name("one_hub") });

const centres = onedesk().centers.reachable();
const search = ref("");

const shown = computed(() => {
  const words = onedesk().centers.search_words(search.value);
  return centres.filter((one) => onedesk().centers.matches({ title: one.name, text: one.line }, words));
});

function open(one) {
  onedesk().centers.open(one.key, one.asked);
}
</script>
