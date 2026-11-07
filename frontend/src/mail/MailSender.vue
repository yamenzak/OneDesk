<template>
  <div v-if="said" :class="folded ? 'rounded-3 border border-outline-gray-1 px-3 py-2.5' : ''">
    <a :href="recordRoute(said.doctype, said.name)" class="flex items-center gap-2.5">
      <Avatar :image="said.image" :label="said.title" size="lg" />
      <span class="min-w-0 flex-1">
        <span class="block truncate font-medium text-ink-gray-9">{{ said.title }}</span>
        <span class="block text-sm text-ink-gray-5">{{ said.label }}</span>
      </span>
      <span class="lucide-arrow-up-right size-4 text-ink-gray-5" aria-hidden="true" />
    </a>
    <p v-if="!said.groups.length" class="mt-2 text-sm text-ink-gray-5">{{ __("Nothing open") }}</p>
    <button v-else-if="folded && !opened" type="button" class="mt-1.5 text-sm text-ink-gray-5 hover:underline" @click="opened = true">
      {{ said.groups.map((one) => `${one.label}: ${one.rows.length}${one.more ? "+" : ""}`).join(" · ") }}
    </button>
    <div v-for="group in folded && !opened ? [] : said.groups" :key="group.doctype" class="mt-2.5">
      <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ group.label }}</div>
      <a
        v-for="row in group.rows"
        :key="row.name"
        :href="recordRoute(group.doctype, row.name)"
        class="block rounded-2 py-1 text-sm hover:bg-surface-gray-1"
      >
        <span class="flex items-center gap-2">
          <span class="min-w-0 flex-1 break-all text-ink-gray-8">{{ row.name }}</span>
          <span v-if="row.amount !== null" class="shrink-0 tabular-nums text-ink-gray-8">{{ money(row.amount, row.currency) }}</span>
        </span>
        <span class="flex items-center gap-2 text-ink-gray-5">
          <span v-if="row.status && row.status !== row.name">{{ __(row.status) }}</span>
          <span v-if="row.date">{{ date(row.date) }}</span>
        </span>
      </a>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { Avatar } from "frappe-ui";

import { __, call, date, money, recordRoute } from "../kit";

const props = defineProps({ address: { type: String, default: "" }, folded: { type: Boolean, default: false } });
const opened = ref(false);
const emit = defineEmits(["found"]);
const said = ref(null);

watch(
  () => props.address,
  async (address) => {
    said.value = null;
    if (!address) return;
    const got = await call("onedesk.one_mail.sender.about", { address });
    if (address !== props.address) return;
    said.value = got;
    emit("found", got);
  },
  { immediate: true }
);
</script>
