<template>
  <PageHeaderMobile v-if="phone">
    <template v-if="up" #prefix>
      <PageHeaderBackButton :fallback-route="up" />
    </template>
    <PageHeaderMobileTitle :title="title" />
    <template #suffix><slot name="actions" /></template>
  </PageHeaderMobile>
  <PageHeader v-else>
    <div class="flex min-w-0 items-center gap-2">
      <Breadcrumbs v-if="crumbs.length" data-no-scroll-top :items="[...crumbs, { label: title }]" />
      <PageHeaderTitle v-else :title="title" />
      <Badge v-if="badge && badge.status" :theme="badge.tone" :label="badge.status" />
    </div>
    <div class="flex items-center gap-2"><slot name="actions" /></div>
  </PageHeader>
  <div v-if="phone && badge && badge.status" class="px-4 pt-3">
    <Badge :theme="badge.tone" :label="badge.status" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import {
  Badge,
  Breadcrumbs,
  PageHeader,
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeaderMobileTitle,
  PageHeaderTitle,
} from "frappe-ui";

import { phone } from "../phone";

const props = defineProps({
  title: { type: String, default: "" },
  crumbs: { type: Array, default: () => [] },
  badge: { type: Object, default: null },
});
const up = computed(() => props.crumbs.at(-1)?.route || null);
</script>
