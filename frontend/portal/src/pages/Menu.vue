<template>
  <Head :title="me.party || me.name" />
  <div class="px-4 py-4">
    <List :row-height="44" class="-mx-3 list-row-px-3">
      <ListRows :items="tabs" row-key="path" v-slot="{ item }">
        <ListRow :route="`/${item.path}`">
          <ListCell><span :class="`lucide-${item.icon} size-4 text-ink-gray-5`" aria-hidden="true" /></ListCell>
          <ListCell class="text-base text-ink-gray-8">{{ item.title }}</ListCell>
          <ListCell />
        </ListRow>
      </ListRows>
    </List>
    <h2 class="mb-1 mt-6 text-sm font-medium text-ink-gray-5">{{ __("Account") }}</h2>
    <List :row-height="44" class="-mx-3 list-row-px-3">
      <ListRows :items="account" row-key="path" v-slot="{ item }">
        <ListRow :route="`/${item.path}`">
          <ListCell><span :class="`lucide-${item.icon} size-4 text-ink-gray-5`" aria-hidden="true" /></ListCell>
          <ListCell class="text-base text-ink-gray-8">{{ item.title }}</ListCell>
          <ListCell />
        </ListRow>
      </ListRows>
    </List>
    <Button class="mt-6 w-full" :label="__('Sign Out')" icon-left="lucide-log-out" href="/logout" />
    <Button class="mt-2 w-full" variant="ghost" :label="__('Privacy Policy')" icon-left="lucide-scale" href="/legal/privacy" />
  </div>
</template>

<script setup>
import { Button } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import Head from "../parts/Head.vue";
import { boot } from "../words";

const { tabs = [], account = [], me = {} } = boot();
</script>
