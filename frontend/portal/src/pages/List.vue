<template>
  <!-- One tab: its kind's own list, as erpnext and frappe give it to the
       reader (one/portal.py `rows`), searched and a page at a time. Modelled on Helpdesk's customer
       ticket list: frappe-ui's ListView with the search in the head. -->
  <Head :title="title">
    <template #actions>
      <TextInput v-if="!phone" v-model="txt" type="search" :placeholder="__('Search')" class="w-60">
        <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
      </TextInput>
      <Button v-if="page?.add" variant="solid" :label="page.add.label" :route="`/${page.add.to}`" />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-4xl px-4 py-4 sm:px-6">
    <TextInput v-if="phone" v-model="txt" type="search" :placeholder="__('Search')" class="mb-3">
      <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
    </TextInput>
    <Loading v-if="!page" />
    <template v-else-if="rows.length">
      <List :columns="phone ? ['minmax(0,1fr)', 'auto'] : ['minmax(0,1fr)', '9rem', '9rem']" :row-height="phone ? undefined : 52" class="-mx-3 list-row-px-3">
        <ListHeader v-if="!phone">
          <ListHeaderCell>{{ page.columns[0] }}</ListHeaderCell>
          <ListHeaderCell>{{ page.columns[1] }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ page.columns[2] }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" v-slot="{ item }">
          <ListRow :route="item.to ? `/${item.to}` : undefined">
            <ListCell class="flex-col !items-start gap-0.5 py-1">
              <span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
              <span v-if="item.line" class="w-full truncate text-sm text-ink-gray-5">{{ item.line }}</span>
              <Badge v-if="phone && item.status" class="mt-1" :theme="item.tone" :label="item.status" />
            </ListCell>
            <ListCell v-if="!phone"><Badge v-if="item.status" :theme="item.tone" :label="item.status" /></ListCell>
            <ListCell class="justify-end text-base tabular-nums text-ink-gray-7">{{ item.figure }}</ListCell>
          </ListRow>
        </ListRows>
      </List>
      <Button v-if="page.more" class="mt-4" :label="__('Show More')" :loading="loading" @click="more" />
    </template>
    <Empty v-else :title="txt ? __('Nothing matches') : __('Nothing here yet')" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Badge, Button, TextInput, debounce } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import { phone } from "../phone";
import { boot } from "../words";

const props = defineProps({ kind: { type: String, required: true } });

const title = computed(() => boot().tabs?.find((tab) => tab.path === props.kind)?.title || "");
const page = ref(null);
const rows = ref([]);
const txt = ref("");
const loading = ref(false);

async function load(start = 0) {
  loading.value = true;
  try {
    const got = await call("rows", { kind: props.kind, txt: txt.value, start });
    page.value = got;
    rows.value = start ? [...rows.value, ...got.rows] : got.rows;
  } finally {
    loading.value = false;
  }
}
const more = () => load(rows.value.length);

watch(() => props.kind, () => {
  txt.value = "";
  page.value = null;
  load();
}, { immediate: true });
watch(txt, debounce(() => load(), 300));
</script>
