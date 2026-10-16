<template>
  <!-- A quotation, order, invoice, shipment or purchase document, through
       erpnext's own page context (one/portal.py `record`): its Badge and
       buttons in the head, then its facts, items, totals, terms and files.
       Modelled on Stripe's hosted invoice page: what it is and what to
       pay at the top, its lines under it. -->
  <Head :title="name" :crumbs="[{ label: tab, route: `/${kind}` }]" :badge="doc">
    <template #actions>
      <Button
        v-for="one in doc?.actions || []"
        :key="one.href"
        :label="phone && one.icon ? undefined : one.label"
        :aria-label="one.label"
        :icon="phone && one.icon ? `lucide-${one.icon}` : undefined"
        :icon-left="!phone && one.icon ? `lucide-${one.icon}` : undefined"
        :variant="one.solid ? 'solid' : 'subtle'"
        :href="one.href"
      />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <template v-else>
      <Facts :facts="doc.facts" />
      <List :columns="phone ? ['minmax(0,1fr)', 'auto'] : ['minmax(0,1fr)', '7rem', '8rem', '9rem']" class="mt-6 list-row-px-0">
        <ListHeader>
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell v-if="!phone" class="justify-end">{{ __("Quantity") }}</ListHeaderCell>
          <ListHeaderCell v-if="!phone" class="justify-end">{{ __("Rate") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="doc.items" :row-key="(item, index) => index" v-slot="{ item }">
          <ListRow>
            <ListCell class="flex-col !items-start gap-0.5 py-1.5">
              <span class="text-base text-ink-gray-8">{{ item.item }}</span>
              <span v-if="item.about" class="text-sm text-ink-gray-5">{{ item.about }}</span>
              <span v-if="phone" class="text-sm text-ink-gray-5">{{ item.qty }} {{ item.uom }} × {{ item.rate }}</span>
            </ListCell>
            <ListCell v-if="!phone" class="justify-end gap-1 tabular-nums text-base text-ink-gray-7">
              {{ item.qty }} <span class="text-sm text-ink-gray-5">{{ item.uom }}</span>
            </ListCell>
            <ListCell v-if="!phone" class="justify-end tabular-nums text-base text-ink-gray-7">{{ item.rate }}</ListCell>
            <ListCell class="justify-end tabular-nums text-base text-ink-gray-8">{{ item.amount }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
      <dl class="ms-auto mt-4 grid w-full max-w-xs grid-cols-[1fr_auto] gap-x-6 gap-y-2 border-t border-outline-gray-1 pt-4">
        <template v-for="one in doc.totals" :key="one.label">
          <dt :class="one.strong ? 'text-base font-medium text-ink-gray-9' : 'text-base text-ink-gray-6'">{{ one.label }}</dt>
          <dd :class="['text-end tabular-nums', one.strong ? 'text-base font-semibold text-ink-gray-9' : 'text-base text-ink-gray-7']">{{ one.value }}</dd>
        </template>
      </dl>
      <section v-if="doc.terms" class="mt-8">
        <h2 class="mb-2 text-base font-medium text-ink-gray-9">{{ doc.terms_label }}</h2>
        <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.terms" />
      </section>
      <section v-if="doc.files.length" class="mt-8">
        <h2 class="mb-2 text-base font-medium text-ink-gray-9">{{ __("Files") }}</h2>
        <div class="flex flex-wrap gap-2">
          <Button v-for="one in doc.files" :key="one.url" :label="one.name" icon-left="lucide-paperclip" :href="one.url" target="_blank" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import Empty from "../parts/Empty.vue";
import Facts from "../parts/Facts.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import { phone } from "../phone";
import { boot } from "../words";

const props = defineProps({ kind: { type: String, required: true }, name: { type: String, required: true } });

const tab = computed(() => boot().tabs?.find((one) => one.path === props.kind)?.title || "");
const doc = ref(null);
const failed = ref(false);

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
