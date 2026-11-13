<template>
  <Page wide data-tour="one-home">
    <Loading v-if="!said" />
    <template v-else>
      <Section v-if="said.needs.length" :title="__('The Workspace Needs You')" icon="lucide-triangle-alert" :aside="said.needs.length" class="mt-2" data-tour="one-home-needs">
        <div class="flex flex-col gap-2">
          <button v-for="one in said.needs" :key="one.what" type="button" class="block w-full text-start" @click="go(one.route)">
            <OneAlert colour="yellow">
              <div class="font-medium">{{ one.what }}</div>
              <div class="text-ink-gray-6">{{ one.detail }}</div>
            </OneAlert>
          </button>
        </div>
      </Section>

      <Section v-if="said.glance.length" :title="__('The Workspace')" icon="lucide-building-2" data-tour="one-home-glance">
        <Figures :figures="glance" :columns="glance.length" />
      </Section>

      <Section v-if="said.approvals.length" :title="__('Waiting for Your Approval')" icon="lucide-inbox" :aside="said.waiting" data-tour="one-home-approvals">
        <Rows :rows="approvals" />
      </Section>

      <Section v-if="asked.length" :title="__('Asked of You')" icon="lucide-inbox" :aside="asked.length" data-tour="one-home-asked">
        <Rows :rows="asked" />
      </Section>

      <Section :title="__('Announcements')" icon="lucide-megaphone" :action="{ text: true, label: __('All Announcements'), onClick: () => go('/desk/note') }" data-tour="one-home-announcements">
        <div v-if="said.announcements.length" class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <button v-for="one in said.announcements" :key="one.name" type="button" :class="CARD" class="flex flex-col gap-1 text-start" @click="go('/desk/note')">
            <div class="truncate text-base font-medium text-ink-gray-8">{{ one.title }}</div>
            <div class="line-clamp-3 text-base text-ink-gray-6">{{ one.text }}</div>
            <div class="mt-1 text-sm text-ink-gray-5">{{ one.by }} · {{ ago(one.on) }}</div>
          </button>
        </div>
        <div v-else class="py-3 text-base text-ink-gray-5">{{ __("Nothing is being announced.") }}</div>
      </Section>

      <Section v-if="said.news.length" :title="__('New in Your Apps')" icon="lucide-newspaper" :aside="said.news.length" data-tour="one-home-news">
        <Rows :rows="news" />
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";

import { Figures, Loading, OneAlert, Page, Rows, Section, __, ago, followList, get, go, newDoc, onDesk, onedesk, shortDate } from "../kit";

const props = defineProps({ onTitle: Function, onActions: Function });

const CARD = "rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3";

const said = ref(null);

async function load() {
  said.value = await get("onedesk.one.home.read");
  props.onTitle?.({ title: __("Home") });
  props.onActions?.(said.value.administers ? [{ label: __("New Announcement"), primary: true, onClick: () => newDoc("Note") }] : []);
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Leave Application", "Expense Claim", "Workflow Action", "Note", "Email Account"].map((one) => followList(one, soon));
stop.push(onDesk("one-version-seen", soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const open = (doctype, name) => `/desk/${slug(doctype)}/${encodeURIComponent(name)}`;

const glance = computed(() =>
  said.value.glance.map((one) => ({
    title: one.title,
    value: one.value,
    note: one.note || undefined,
    bar: one.bar,
    route: one.route,
    action: one.key === "apps" ? { icon: "lucide-arrow-up-right", label: one.title, onClick: () => onedesk().apps.configure() } : undefined,
  }))
);

const approvals = computed(() =>
  said.value.approvals.map((one) => ({
    key: `${one.doctype}-${one.name}`,
    label: one.title,
    sub: __(one.doctype),
    dot: "amber",
    value: __("Asked {0}", [ago(one.since)]),
    route: open(one.doctype, one.name),
  }))
);

// Asked of You: each file still wanted from the reader by an open file
// request (one_cloud/file_requests.asked_of), answered in OneCloud's dialog.
const asked = computed(() =>
  said.value.asked.flatMap((request) =>
    request.items
      .filter((item) => !item.sent || item.several)
      .map((item) => ({
        key: `${request.name}-${item.name}`,
        label: item.label,
        sub: `${request.title} · ${request.by}`,
        dot: request.overdue ? "red" : "amber",
        value: request.due_date ? __("Due {0}", [shortDate(request.due_date)]) : "",
        onClick: () => answer(request, item),
      }))
  )
);

async function answer(request, item) {
  await frappe.require(onedesk().cloud_assets);
  onedesk().cloud.answer(request, item, load);
}

const news = computed(() =>
  said.value.news.map((one) => ({
    key: one.module,
    label: one.module,
    sub: one.title,
    dot: "blue",
    value: one.version,
    onClick: () => onedesk().centers.open("updates", { module: one.module }),
  }))
);
</script>
