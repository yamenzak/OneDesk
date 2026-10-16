<template>
  <!-- A customer's project (one_project/portal.py `page`).
       Modelled on Basecamp's client view of a project: its photos beside how
       far along it is and when it ends, then its milestones as a line of
       dates, its sub-projects and tasks, and beside them its order and
       invoices, the time a member is shown and its files. -->
  <Head :title="doc?.title || ''" :crumbs="[{ label: tab, route: '/projects' }]" :badge="doc" />
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <!-- On a phone the two columns are one, what it comes to first. -->
      <div class="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
        <Gallery v-if="doc.media.length" :media="doc.media" />

        <Card v-if="doc.milestones.length" :title="__('Milestones')" icon="lucide-flag">
          <ol class="relative flex flex-col gap-5 border-s border-outline-gray-2 ps-6">
            <li v-for="(one, i) in doc.milestones" :key="i" class="relative">
              <span
                :class="[
                  'absolute -start-[2.03rem] top-0.5 grid size-4 place-items-center rounded-full border',
                  one.tone === 'green' ? 'border-transparent bg-surface-gray-10 text-ink-base' : 'border-outline-gray-3 bg-surface-base',
                ]"
              >
                <span v-if="one.tone === 'green'" class="lucide-check size-3" aria-hidden="true" />
              </span>
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-base font-medium text-ink-gray-9">{{ one.subject }}</p>
                <Badge :theme="one.tone" :label="one.status" />
              </div>
              <p v-if="one.due" :class="['text-sm', one.late ? 'text-ink-red-6' : 'text-ink-gray-5']">{{ one.due }}</p>
            </li>
          </ol>
        </Card>

        <Card v-if="doc.projects.length" :title="__('Sub-projects')" icon="lucide-folder-kanban" :count="doc.projects.length" flush>
          <RouterLink
            v-for="one in doc.projects"
            :key="one.name"
            :to="`/projects/${one.name}`"
            class="flex items-center gap-4 border-b border-outline-gray-1 px-4 py-3 last:border-b-0 hover:bg-surface-gray-1"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-base font-medium text-ink-gray-9">{{ one.title }}</p>
              <p v-if="one.ends" class="text-sm text-ink-gray-5">{{ one.ends }}</p>
            </div>
            <Progress class="hidden w-32 sm:block" :value="one.share" />
            <span class="w-10 text-end text-sm tabular-nums text-ink-gray-7">{{ one.share }}%</span>
            <Badge :theme="one.tone" :label="one.status" />
          </RouterLink>
        </Card>

        <Card v-if="doc.tasks.length || !doc.projects.length" :title="__('Tasks')" icon="lucide-list-checks" :count="doc.tasks.length || ''" flush>
          <p v-if="!doc.tasks.length" class="px-4 py-6 text-base text-ink-gray-5">{{ __("No tasks yet") }}</p>
          <div
            v-for="(one, i) in doc.tasks"
            :key="i"
            :class="['flex items-center gap-3 border-b border-outline-gray-1 py-2.5 pe-4 last:border-b-0', one.under ? 'ps-10' : 'ps-4']"
          >
            <span
              :class="[
                'grid size-4 shrink-0 place-items-center rounded-full border',
                one.tone === 'green' ? 'border-transparent bg-surface-gray-10 text-ink-base' : 'border-outline-gray-3',
              ]"
            >
              <span v-if="one.tone === 'green'" class="lucide-check size-3" aria-hidden="true" />
            </span>
            <span :class="['min-w-0 flex-1 truncate text-base', one.tone === 'green' ? 'text-ink-gray-5' : 'text-ink-gray-8']">{{ one.subject }}</span>
            <span v-if="one.due" :class="['shrink-0 text-sm', one.late ? 'text-ink-red-6' : 'text-ink-gray-5']">{{ one.due }}</span>
            <Badge :theme="one.tone" :label="one.status" />
          </div>
        </Card>
      </div>

      <aside class="contents lg:flex lg:flex-col lg:gap-5">
        <Card class="order-first lg:order-none">
          <p class="text-sm text-ink-gray-6">{{ __("Progress") }}</p>
          <p class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">{{ doc.share }}%</p>
          <Progress class="mt-3" :value="doc.share" size="md" />
          <p v-if="doc.total" class="mt-2 text-sm text-ink-gray-6">{{ __("{0} of {1} tasks done", [doc.done, doc.total]) }}</p>
          <dl class="mt-4 flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
            <div v-if="doc.ends" class="flex justify-between gap-4">
              <dt class="text-sm text-ink-gray-5">{{ __("Expected End") }}</dt>
              <dd class="text-end text-sm text-ink-gray-8">
                {{ doc.ends }}
                <span v-if="doc.when" :class="['block', doc.late ? 'text-ink-red-6' : 'text-ink-gray-5']">{{ doc.when }}</span>
              </dd>
            </div>
            <div v-if="doc.parent" class="flex justify-between gap-4">
              <dt class="text-sm text-ink-gray-5">{{ __("Part of") }}</dt>
              <dd class="text-end text-sm">
                <RouterLink :to="`/projects/${doc.parent.name}`" class="text-ink-gray-8 underline underline-offset-2">{{ doc.parent.title }}</RouterLink>
              </dd>
            </div>
          </dl>
        </Card>

        <Card v-if="doc.order || doc.invoices.length" :title="__('Order and Invoices')" flush>
          <LinkRow v-for="one in money" :key="one.to" :to="one.to" :name="one.name" :line="one.line" :status="one.status" :tone="one.tone" />
        </Card>

        <Card v-if="doc.time" :title="__('Time')" icon="lucide-clock" :count="__('{0} hours', [doc.time.hours])" flush>
          <p v-if="!doc.time.rows.length" class="px-4 py-4 text-sm text-ink-gray-5">{{ __("No time yet") }}</p>
          <div v-for="(one, i) in doc.time.rows" :key="i" class="flex justify-between gap-3 border-b border-outline-gray-1 px-4 py-2.5 text-sm last:border-b-0">
            <span class="min-w-0">
              <span class="block truncate text-ink-gray-8">{{ one.what }}</span>
              <span class="text-ink-gray-5">{{ one.day }}</span>
            </span>
            <span class="shrink-0 tabular-nums text-ink-gray-8">{{ one.hours }}</span>
          </div>
        </Card>

        <Card v-if="doc.files.length" :title="__('Files')" icon="lucide-paperclip" flush>
          <a
            v-for="one in doc.files"
            :key="one.url"
            :href="one.url"
            target="_blank"
            rel="noopener"
            class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-2.5 text-sm text-ink-gray-8 last:border-b-0 hover:bg-surface-gray-1"
          >
            <span class="lucide-file size-4 text-ink-gray-5" aria-hidden="true" />
            <span class="truncate">{{ one.name }}</span>
          </a>
        </Card>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Badge, Progress } from "frappe-ui";

import { call } from "../call";
import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Gallery from "../parts/Gallery.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import LinkRow from "../parts/LinkRow.vue";
import { __, boot } from "../words";

const props = defineProps({ name: { type: String, required: true } });

const tab = computed(() => boot().tabs?.find((one) => one.path === "projects")?.title || __("Projects"));
const doc = ref(null);
const failed = ref(false);

const money = computed(() => [
  ...(doc.value.order ? [{ name: doc.value.order.name, line: `${__("Order")} · ${doc.value.order.total}`, icon: "package", to: `/orders/${doc.value.order.name}` }] : []),
  ...doc.value.invoices.map((one) => ({ name: one.name, line: `${one.date} · ${one.total}`, icon: "receipt", tone: one.tone, status: one.status, to: `/invoices/${one.name}` })),
]);

watch(
  () => props.name,
  async () => {
    doc.value = null;
    failed.value = false;
    try {
      doc.value = await call("onedesk.one_project.portal.page", { project: props.name });
    } catch {
      failed.value = true;
    }
  },
  { immediate: true },
);
</script>
