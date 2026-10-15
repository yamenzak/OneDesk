<template>
  <!-- What the reader has: a row a tab with anything in it, how many, and
       how many wait on them (one/portal.py `home`).
       Modelled on Helpdesk's customer portal: a line a thing they have. -->
  <Head :title="__('Home')" />
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <p class="mb-5 text-p-base text-ink-gray-6">{{ __("Hello, {0}. Everything you have with us, in one place.", [first]) }}</p>
    <Loading v-if="said.loading && !said.data" />
    <List v-else-if="said.data?.length" :row-height="40" class="-mx-3 list-row-px-3">
      <ListRows :items="said.data" row-key="path" v-slot="{ item }">
        <ListRow :route="`/${item.path}`">
          <ListCell><span :class="`lucide-${item.icon} size-4 text-ink-gray-5`" aria-hidden="true" /></ListCell>
          <ListCell class="text-base text-ink-gray-8">{{ item.title }}</ListCell>
          <ListCell class="gap-3">
            <Badge v-if="item.waiting" theme="amber" :label="item.waiting" />
            <span class="text-base tabular-nums text-ink-gray-6">{{ item.count }}</span>
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
    <Empty v-else :title="__('Nothing here yet')" :line="__('What we send you will be here.')" />
  </div>
</template>

<script setup>
import { Badge, createResource } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import { boot } from "../words";

const first = (boot().me?.name || "").split(" ")[0];
const said = createResource({ url: "onedesk.one.portal.home", auto: true });
</script>
