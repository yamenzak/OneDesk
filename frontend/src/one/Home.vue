<template>
  <Page wide data-tour="one-home">
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="cards.length" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" data-tour="one-home-counts">
        <NumberCard v-for="card in cards" :key="card.key" :title="card.title" :value="card.value" :format="count" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>

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

      <div class="grid grid-cols-1 gap-x-10 lg:grid-cols-2">
        <Section v-if="'tasks' in said.counts" :title="__('Your Tasks')" icon="lucide-circle-check" :aside="said.counts.tasks || null" :action="{ text: true, label: __('My Tasks'), onClick: () => go('/desk/my-tasks') }" data-tour="one-home-tasks">
          <Rows :rows="tasks" :empty="__('Nothing is due today.')" />
        </Section>
        <Section v-if="'meetings' in said.counts" :title="__('Today')" icon="lucide-calendar" :aside="said.counts.meetings || null" :action="{ text: true, label: __('OneCalendar'), onClick: () => go('/desk/onecalendar') }" data-tour="one-home-today">
          <Rows :rows="meetings" :empty="__('Nothing is on your calendar today.')" />
        </Section>
      </div>

      <Section v-if="said.approvals.length" :title="__('Waiting for Your Approval')" icon="lucide-inbox" :aside="said.counts.approvals">
        <Rows :rows="approvals" />
      </Section>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { NumberCard } from "frappe-ui/charts";

import { Loading, OneAlert, Page, Rows, Section, __, ago, clock, count, date, followList, get, go, isPast, me, newDoc } from "../kit";

const props = defineProps({ onTitle: Function, onActions: Function });

const said = ref(null);

async function load() {
  said.value = await get("onedesk.one.home.read");
  props.onTitle?.({ title: __("Home") });
  const counts = said.value.counts;
  props.onActions?.([
    ...("tasks" in counts ? [{ label: __("New Task"), primary: true, onClick: () => newDoc("Task") }] : []),
    ...("meetings" in counts ? [{ label: __("New Event"), primary: !("tasks" in counts), onClick: () => newDoc("Event") }] : []),
  ]);
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Task", "Event", "Leave Application", "Expense Claim", "Workflow Action", "AI Proposal", "Email Account"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const open = (doctype, name) => `/desk/${slug(doctype)}/${encodeURIComponent(name)}`;

const CARDS = () => ({
  tasks: { title: __("Tasks Due or Late"), route: "/desk/my-tasks" },
  meetings: { title: __("Meetings Today"), route: "/desk/onecalendar" },
  documents: { title: __("Documents Waiting"), route: "/desk/intake?box=waiting" },
  suggestions: { title: __("OneAI Suggestions"), route: `/desk/ai-proposal?state=Proposed&asked_by=${encodeURIComponent(me())}` },
  approvals: { title: __("Approvals Waiting"), route: null },
});

const cards = computed(() => {
  const named = CARDS();
  return Object.entries(said.value.counts).map(([key, value]) => {
    const first = said.value.approvals[0];
    const route = named[key].route || (first ? `/desk/${slug(first.doctype)}` : "/desk/leave-application");
    return { key, value, title: named[key].title, route };
  });
});

const tasks = computed(() =>
  said.value.tasks.map((one) => ({
    key: one.name,
    label: one.subject,
    sub: one.project || "",
    dot: one.due && isPast(one.due) ? "red" : "amber",
    value: one.due ? date(one.due) : "",
    under: one.due && isPast(one.due) ? __("Late") : __("Today"),
    route: open("Task", one.name),
  }))
);

const meetings = computed(() =>
  said.value.meetings.map((one) => ({
    key: `${one.doctype}-${one.name}-${one.start}`,
    label: one.title,
    dot: "blue",
    value: one.all_day ? __("All Day") : one.end ? `${clock(one.start)} – ${clock(one.end)}` : clock(one.start),
    route: open(one.doctype, one.name),
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
</script>
