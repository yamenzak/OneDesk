<template>
  <Head :title="__('Home')" />
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <div class="mb-6">
      <h1 class="text-2xl font-semibold text-ink-gray-9">{{ __("Hello, {0}", [first]) }}</h1>
      <p v-if="party" class="mt-1 text-base text-ink-gray-6">{{ party }}</p>
    </div>
    <Loading v-if="said.loading && !said.data" />
    <template v-else-if="said.data?.tiles.length">
      <div class="grid grid-flow-dense grid-cols-2 gap-3 lg:grid-cols-4">
        <RouterLink
          v-for="tile in said.data.tiles"
          :key="tile.path"
          :to="`/${tile.path}`"
          :class="tile.figure && 'col-span-2 lg:col-span-1'"
          class="flex flex-col gap-2 rounded-5 border border-outline-gray-2 bg-surface-base px-4 py-3 hover:border-outline-gray-3 hover:bg-surface-gray-1"
        >
          <span class="flex items-center gap-2 text-sm text-ink-gray-6">
            <span :class="`lucide-${tile.icon} size-4 text-ink-gray-5`" aria-hidden="true" />
            <span class="truncate">{{ tile.title }}</span>
          </span>
          <span v-if="tile.figure" class="truncate text-xl font-semibold tabular-nums text-ink-gray-9">{{ tile.figure }}</span>
          <span v-else class="text-xl font-semibold tabular-nums text-ink-gray-9">{{ tile.count }}</span>
          <span class="flex min-h-5 items-center gap-2 text-sm text-ink-gray-5">
            <template v-if="tile.figure">{{ tile.figure_label }} · {{ __("{0} in all", [tile.count]) }}</template>
            <Badge v-else-if="tile.waiting" theme="amber" :label="tile.waiting" />
          </span>
        </RouterLink>
      </div>

      <div class="mt-6 grid gap-5 lg:grid-cols-2">
        <Card :title="__('Needs You')" icon="lucide-bell" :count="said.data.asks.length + said.data.more_asks || ''" flush>
          <div v-if="!said.data.asks.length" class="flex items-center gap-3 px-4 py-6 text-base text-ink-gray-6">
            <span class="lucide-circle-check size-5 text-ink-green-6" aria-hidden="true" />{{ __("You're all caught up.") }}
          </div>
          <RouterLink
            v-for="one in said.data.asks"
            :key="one.to"
            :to="`/${one.to}`"
            class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3 last:border-b-0 hover:bg-surface-gray-1"
          >
            <Thumb :icon="one.icon" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-base font-medium text-ink-gray-9">{{ one.title }}</p>
              <p class="truncate text-sm text-ink-gray-5">
                {{ one.kind }}<template v-if="one.figure"> · {{ one.figure }}</template>
              </p>
              <p v-if="one.when?.text" :class="['text-sm', one.when.late ? 'text-ink-red-6' : 'text-ink-gray-6']">{{ one.when.text }}</p>
            </div>
            <Button :label="one.button" class="hidden shrink-0 sm:inline-flex" />
          </RouterLink>
        </Card>

        <Card :title="__('Recent')" icon="lucide-history" flush>
          <RouterLink
            v-for="one in said.data.recent"
            :key="one.to"
            :to="`/${one.to}`"
            class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3 last:border-b-0 hover:bg-surface-gray-1"
          >
            <Thumb :icon="one.icon" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-base font-medium text-ink-gray-9">{{ one.title }}</p>
              <p class="truncate text-sm text-ink-gray-5">{{ one.kind }} · {{ one.date }}</p>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-1">
              <span class="text-base tabular-nums text-ink-gray-8">{{ one.figure }}</span>
              <Badge v-if="one.status" :theme="one.tone" :label="one.status" />
            </div>
          </RouterLink>
        </Card>
      </div>
    </template>
    <Empty v-else :title="__('Nothing here yet')" :line="__('What we send you will be here.')" />
  </div>
</template>

<script setup>
import { Badge, Button, createResource } from "frappe-ui";

import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import Thumb from "../parts/Thumb.vue";
import { boot } from "../words";

const first = (boot().me?.name || "").split(" ")[0];
const party = boot().me?.party || "";
const said = createResource({ url: "onedesk.one_portal.portal.home", auto: true });
</script>
