<template>
  <!-- A customer's project (one_project/portal.py `page`): how far along it is
       and when it ends beside its photos, then its milestones, sub-projects,
       tasks, the time and files a member is shown, its order and invoices.
       Modelled on Basecamp's client view of a project. -->
  <Head :title="doc?.title || ''" :crumbs="[{ label: tab, route: '/projects' }]" :badge="doc" />
  <div class="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <template v-else>
      <div :class="['grid gap-6', doc.media.length && 'md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]']">
        <div class="flex flex-col gap-5">
          <Facts :facts="facts" />
          <Progress :value="doc.share" size="md" />
        </div>
        <Gallery v-if="doc.media.length" :media="doc.media" />
      </div>
      <Section v-if="doc.milestones.length" :title="__('Milestones')">
        <Rows :rows="doc.milestones.map(task)" />
      </Section>
      <Section v-if="doc.projects.length" :title="__('Sub-projects')">
        <Rows :rows="doc.projects.map((one) => ({ title: one.title, line: one.ends, tone: one.tone, status: one.status, figure: `${one.share}%`, to: `/projects/${one.name}` }))" />
      </Section>
      <Section v-if="doc.tasks.length || !doc.projects.length" :title="__('Tasks')">
        <Rows v-if="doc.tasks.length" :rows="doc.tasks.map(task)" />
        <p v-else class="text-p-sm text-ink-gray-5">{{ __("No tasks yet") }}</p>
      </Section>
      <Section v-if="doc.time" :title="__('Time')" :aside="__('{0} hours', [doc.time.hours])">
        <Rows v-if="doc.time.rows.length" :rows="doc.time.rows.map((one) => ({ title: one.what, line: one.day, figure: one.hours }))" />
        <p v-else class="text-p-sm text-ink-gray-5">{{ __("No time yet") }}</p>
      </Section>
      <Section v-if="doc.files.length" :title="__('Files')">
        <Rows :rows="doc.files.map((one) => ({ title: one.name, href: one.url }))" />
      </Section>
      <Section v-if="doc.order || doc.invoices.length" :title="__('Order and Invoices')">
        <Rows :rows="money" />
      </Section>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Progress } from "frappe-ui";

import { call } from "../call";
import Empty from "../parts/Empty.vue";
import Facts from "../parts/Facts.vue";
import Gallery from "../parts/Gallery.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import Rows from "../parts/Rows.vue";
import Section from "../parts/Section.vue";
import { __, boot } from "../words";

const props = defineProps({ name: { type: String, required: true } });

const tab = computed(() => boot().tabs?.find((one) => one.path === "projects")?.title || __("Projects"));
const doc = ref(null);
const failed = ref(false);

const task = (one) => ({ title: one.subject, tone: one.tone, status: one.status, figure: one.due, late: one.late, under: one.under });

const facts = computed(() => {
  const out = [{ label: __("Progress"), value: doc.value.total ? `${doc.value.share}% · ${__("{0} of {1} tasks done", [doc.value.done, doc.value.total])}` : `${doc.value.share}%` }];
  if (doc.value.ends) out.push({ label: __("Expected End"), value: doc.value.when ? `${doc.value.ends} · ${doc.value.when}` : doc.value.ends });
  if (doc.value.parent) out.push({ label: __("Part of"), value: doc.value.parent.title, to: `/projects/${doc.value.parent.name}` });
  return out;
});

const money = computed(() => [
  ...(doc.value.order ? [{ title: doc.value.order.name, line: __("Order"), figure: doc.value.order.total, to: `/orders/${doc.value.order.name}` }] : []),
  ...doc.value.invoices.map((one) => ({ title: one.name, line: one.date, tone: one.tone, status: one.status, figure: one.total, to: `/invoices/${one.name}` })),
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
