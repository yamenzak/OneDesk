<template>
  <!-- One tab: its kind's own list, as erpnext and frappe give it to the
       reader (one/portal.py `rows`), searched, narrowed to a state and a page
       at a time. Modelled on Shopify's order list in a customer account and
       Stripe's invoices: the states as tabs with their counts over a table in
       a card, each row its number and date, what it is for, its state, the
       date it looks ahead to and its total. -->
  <Head :title="title">
    <template #actions>
      <TextInput v-if="!phone" v-model="txt" type="search" :placeholder="__('Search')" class="w-60">
        <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
      </TextInput>
      <Button v-if="page?.add" variant="solid" :label="page.add.label" icon-left="lucide-plus" :route="`/${page.add.to}`" />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <TextInput v-if="phone" v-model="txt" type="search" :placeholder="__('Search')" class="mb-3">
      <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
    </TextInput>
    <div v-if="tabs.length" class="mb-4 overflow-x-auto">
      <TabButtons v-model="state" :options="tabs" />
    </div>
    <Loading v-if="!page" />
    <Card v-else-if="rows.length" flush>
      <List :columns="columns" :row-height="phone ? undefined : 60" class="list-row-px-4">
        <ListHeader v-if="!phone">
          <template v-if="dealt">
            <ListHeaderCell>{{ page.columns[0] }}</ListHeaderCell>
            <ListHeaderCell>{{ __("Items") }}</ListHeaderCell>
            <ListHeaderCell>{{ page.columns[1] }}</ListHeaderCell>
            <ListHeaderCell v-if="ahead">{{ __("Next") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end">{{ page.columns[2] }}</ListHeaderCell>
          </template>
          <template v-else>
            <ListHeaderCell>{{ page.columns[0] }}</ListHeaderCell>
            <ListHeaderCell>{{ page.columns[1] }}</ListHeaderCell>
            <ListHeaderCell class="justify-end">{{ page.columns[2] }}</ListHeaderCell>
          </template>
        </ListHeader>
        <ListRows :items="rows" v-slot="{ item }">
          <ListRow :route="item.to ? `/${item.to}` : undefined">
            <!-- A phone: the name and its Badge, what it is for under it, the total at the end. -->
            <template v-if="phone">
              <ListCell class="flex-col !items-start gap-1 py-3">
                <span class="w-full truncate text-base font-medium text-ink-gray-9">{{ item.title }}</span>
                <span class="w-full truncate text-sm text-ink-gray-6">{{ dealt ? itemLine(item) : item.line }}</span>
                <span class="flex items-center gap-2">
                  <Badge v-if="item.status" :theme="item.tone" :label="item.status" />
                  <span v-if="item.when?.text" :class="['text-sm', item.when.late ? 'text-ink-red-6' : 'text-ink-gray-5']">{{ item.when.text }}</span>
                </span>
              </ListCell>
              <ListCell class="justify-end text-base font-medium tabular-nums text-ink-gray-9">{{ item.figure }}</ListCell>
            </template>
            <template v-else-if="dealt">
              <ListCell class="gap-3">
                <Thumb :icon="icon" />
                <span class="flex min-w-0 flex-col">
                  <span class="truncate text-base font-medium text-ink-gray-9">{{ item.title }}</span>
                  <span class="text-sm text-ink-gray-5">{{ item.date }}</span>
                </span>
              </ListCell>
              <ListCell class="gap-2">
                <span class="truncate text-base text-ink-gray-7">{{ item.item }}</span>
                <span v-if="item.others" class="shrink-0 rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6">+{{ item.others }}</span>
              </ListCell>
              <ListCell><Badge v-if="item.status" :theme="item.tone" :label="item.status" /></ListCell>
              <ListCell v-if="ahead" :class="['text-sm', item.when?.late ? 'text-ink-red-6' : 'text-ink-gray-6']">{{ item.when?.text }}</ListCell>
              <ListCell class="justify-end text-base font-medium tabular-nums text-ink-gray-9">{{ item.figure }}</ListCell>
            </template>
            <template v-else>
              <ListCell class="gap-3">
                <Thumb :icon="icon" />
                <span class="flex min-w-0 flex-col">
                  <span class="truncate text-base font-medium text-ink-gray-9">{{ item.title }}</span>
                  <span v-if="item.line" class="truncate text-sm text-ink-gray-5">{{ item.line }}</span>
                </span>
              </ListCell>
              <ListCell><Badge v-if="item.status" :theme="item.tone" :label="item.status" /></ListCell>
              <ListCell class="justify-end gap-3 text-base tabular-nums text-ink-gray-8">
                <Progress v-if="page.doctype === 'Project'" class="w-24" :value="parseInt(item.figure) || 0" />
                {{ item.figure }}
              </ListCell>
            </template>
          </ListRow>
        </ListRows>
      </List>
      <template v-if="page.more" #foot>
        <Button :label="__('Show More')" :loading="loading" @click="more" />
      </template>
    </Card>
    <Empty v-else :title="txt || state ? __('Nothing matches') : __('Nothing here yet')" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Badge, Button, Progress, TabButtons, TextInput, debounce } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import Thumb from "../parts/Thumb.vue";
import { phone } from "../phone";
import { __, boot } from "../words";

const props = defineProps({ kind: { type: String, required: true } });

const tab = computed(() => boot().tabs?.find((one) => one.path === props.kind) || {});
const title = computed(() => tab.value.title || "");
const icon = computed(() => tab.value.icon || "file-text");
const page = ref(null);
const rows = ref([]);
const txt = ref("");
const state = ref("");
const loading = ref(false);

// A quotation, order or bill: its items and the date it looks ahead to have
// columns of their own.
const dealt = computed(() => rows.value.some((row) => row.date !== undefined));
// The Next column only where a row has a date to look ahead to.
const ahead = computed(() => rows.value.some((row) => row.when?.text));
const columns = computed(() => {
  if (phone.value) return ["minmax(0,1fr)", "auto"];
  if (dealt.value && ahead.value) return ["minmax(12rem,1.2fr)", "minmax(0,1.6fr)", "9rem", "10rem", "9rem"];
  if (dealt.value) return ["minmax(12rem,1.2fr)", "minmax(0,1.6fr)", "9rem", "9rem"];
  return ["minmax(0,1fr)", "9rem", "12rem"];
});
const tabs = computed(() => {
  const states = page.value?.states || [];
  if (!states.length) return [];
  return [
    { label: `${__("All")} ${page.value.total}`, value: "" },
    ...states.map((one) => ({ label: `${one.label} ${one.count}`, value: one.label })),
  ];
});
const itemLine = (item) => [item.item, item.others ? `+${item.others}` : ""].filter(Boolean).join(" ");

async function load(start = 0) {
  loading.value = true;
  try {
    const got = await call("rows", { kind: props.kind, txt: txt.value, state: state.value, start });
    page.value = got;
    rows.value = start ? [...rows.value, ...got.rows] : got.rows;
  } finally {
    loading.value = false;
  }
}
const more = () => load(rows.value.length);

watch(() => props.kind, () => {
  txt.value = "";
  state.value = "";
  page.value = null;
  load();
}, { immediate: true });
watch(txt, debounce(() => load(), 300));
watch(state, () => load());
</script>
