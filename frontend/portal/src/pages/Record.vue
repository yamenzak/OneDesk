<template>
  <!-- A quotation, order, invoice, shipment or purchase document, through
       erpnext's own page context (one/portal.py `record`).
       Modelled on Shopify's order page in a customer account, with Stripe's
       invoice summary: where it is on its way across the top, its items and
       totals in one card, and beside them what it comes to (what is left to
       pay, and Pay), its details and the records before and after it. -->
  <Head :title="name" :crumbs="[{ label: tab, route: `/${kind}` }]" :badge="doc">
    <template #actions>
      <Button
        v-for="one in quiet"
        :key="one.href"
        :label="phone && one.icon ? undefined : one.label"
        :aria-label="one.label"
        :icon="phone && one.icon ? `lucide-${one.icon}` : undefined"
        :icon-left="!phone && one.icon ? `lucide-${one.icon}` : undefined"
        :href="one.href"
      />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <!-- On a phone the two columns are one, what it comes to first. -->
      <div class="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
        <Card v-if="doc.steps.length"><Steps :steps="doc.steps" /></Card>

        <Card :title="__('Items')" :count="doc.items.length" flush>
          <ul>
            <li v-for="(item, i) in doc.items" :key="i" class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3 last:border-b-0">
              <Thumb :image="item.image" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-base text-ink-gray-9">{{ item.item }}</p>
                <p v-if="item.about" class="truncate text-sm text-ink-gray-5">{{ item.about }}</p>
                <p class="text-sm tabular-nums text-ink-gray-6">{{ item.qty }} {{ item.uom }} × {{ item.rate }}</p>
              </div>
              <p class="shrink-0 text-base font-medium tabular-nums text-ink-gray-9">{{ item.amount }}</p>
            </li>
          </ul>
          <template #foot>
            <dl class="ms-auto grid max-w-xs grid-cols-[1fr_auto] gap-x-6 gap-y-1.5">
              <template v-for="one in doc.totals" :key="one.label">
                <dt :class="one.strong ? 'text-base font-medium text-ink-gray-9' : 'text-base text-ink-gray-6'">{{ one.label }}</dt>
                <dd :class="['text-end tabular-nums', one.strong ? 'text-base font-semibold text-ink-gray-9' : 'text-base text-ink-gray-7']">{{ one.value }}</dd>
              </template>
            </dl>
          </template>
        </Card>

        <Card v-if="doc.terms" :title="doc.terms_label">
          <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.terms" />
        </Card>
      </div>

      <aside class="contents lg:flex lg:flex-col lg:gap-5">
        <Card class="order-first lg:order-none">
          <p class="text-sm text-ink-gray-6">{{ doc.summary.label }}</p>
          <p class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">{{ doc.summary.value }}</p>
          <p v-if="doc.summary.line" :class="['mt-1 text-sm', doc.summary.late ? 'text-ink-red-6' : 'text-ink-gray-6']">{{ doc.summary.line }}</p>
          <Button v-for="one in solid" :key="one.href" class="mt-4 w-full" variant="solid" size="md" :label="one.label" :href="one.href" />
        </Card>

        <Card :title="__('Details')">
          <dl class="flex flex-col gap-3">
            <div v-for="one in doc.facts" :key="one.label" class="flex justify-between gap-4">
              <dt class="shrink-0 text-sm text-ink-gray-5">{{ one.label }}</dt>
              <dd :class="['text-end text-sm text-ink-gray-8', one.lines && 'whitespace-pre-line']">{{ one.value }}</dd>
            </div>
          </dl>
        </Card>

        <Card v-if="doc.related.length" :title="__('Linked')" flush>
          <LinkRow
            v-for="one in doc.related"
            :key="one.to"
            :to="`/${one.to}`"
            :name="one.name"
            :line="`${one.kind} · ${one.figure}`"
            :status="one.status"
            :tone="one.tone"
          />
        </Card>

        <Card v-if="doc.files.length" :title="__('Files')" flush>
          <a
            v-for="one in doc.files"
            :key="one.url"
            :href="one.url"
            target="_blank"
            rel="noopener"
            class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-2.5 text-sm text-ink-gray-8 last:border-b-0 hover:bg-surface-gray-1"
          >
            <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />
            <span class="truncate">{{ one.name }}</span>
          </a>
        </Card>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { call } from "../call";
import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import LinkRow from "../parts/LinkRow.vue";
import Loading from "../parts/Loading.vue";
import Steps from "../parts/Steps.vue";
import Thumb from "../parts/Thumb.vue";
import { phone } from "../phone";
import { boot } from "../words";

const props = defineProps({ kind: { type: String, required: true }, name: { type: String, required: true } });

const tab = computed(() => boot().tabs?.find((one) => one.path === props.kind)?.title || "");
const doc = ref(null);
const failed = ref(false);
// Pay goes in the summary, under what it pays; the rest in the head.
const solid = computed(() => (doc.value?.actions || []).filter((one) => one.solid));
const quiet = computed(() => (doc.value?.actions || []).filter((one) => !one.solid));

watch(
  () => [props.kind, props.name],
  async () => {
    doc.value = null;
    failed.value = false;
    try {
      doc.value = await call("record", { kind: props.kind, name: props.name });
    } catch {
      failed.value = true;
    }
  },
  { immediate: true },
);
</script>
