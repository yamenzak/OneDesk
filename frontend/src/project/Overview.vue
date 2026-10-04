<template>
  <!-- What the project is and how it is going, as Asana's Overview: the brief,
       its numbers and the team's updates on the left; what needs someone, the
       facts and what sits under it on the right. -->
  <div class="grid gap-x-10 pb-12 pt-2 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <Section :title="__('Brief')">
        <div v-if="said.notes" class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.notes" />
        <button v-else class="text-base text-ink-gray-5 hover:text-ink-gray-8" @click="go(`/desk/project/${said.name}?edit=1`)">{{ __("Add a brief") }}</button>
      </Section>

      <Section :title="__('Numbers')">
        <Figures :figures="figures" />
      </Section>

      <Section v-if="view.months" :title="__('Months')" :aside="__('{0} a month', [money(view.months.fee, said.currency)])">
        <Months :months="view.months" @invoice="(month) => onedesk().project.invoice_month(frm(), month)" />
      </Section>

      <Section v-if="view.milestones?.length" :title="__('Milestones')">
        <Milestones :milestones="view.milestones" />
      </Section>

      <Section :title="__('Updates')">
        <div class="rounded-5 border border-outline-gray-2 p-3">
          <div class="mb-2 flex flex-wrap items-center gap-2">
            <button v-for="one in HEALTHS" :key="one" @click="health = one">
              <Badge :label="__(one)" :theme="HEALTH[one]" :variant="health === one ? 'solid' : 'subtle'" size="md" />
            </button>
          </div>
          <Textarea v-model="note" :rows="2" :placeholder="__('Write an update')" />
          <div class="mt-2 flex justify-end">
            <Button variant="solid" :label="__('Post Update')" :disabled="!note.trim()" :loading="posting" @click="post" />
          </div>
        </div>
        <div v-for="(one, i) in updates" :key="i" class="flex gap-3 border-b border-outline-gray-1 py-4 last:border-0">
          <Avatar :label="one.by" size="md" />
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-2 text-base">
              <span class="font-medium text-ink-gray-8">{{ one.by }}</span>
              <span class="text-sm text-ink-gray-5">{{ date(one.on) }}</span>
            </div>
            <p class="mt-1 text-base leading-relaxed text-ink-gray-7">{{ one.said }}</p>
          </div>
        </div>
      </Section>

      <Section v-if="weekly.length" :title="__('Hours by Week')" :aside="hours(view.weekly.total)">
        <div class="h-56">
          <BarChart :data="weekly" x="week" :y="['hours']" :series-config="{ hours: { label: __('Hours') } }" />
        </div>
      </Section>
    </div>

    <div class="min-w-0">
      <Section :title="__('Needs You')" :aside="view.needs.length || ''">
        <Rows :rows="needs" :empty="__('Nothing needs you')" />
      </Section>
      <Section :title="__('About')">
        <Facts :facts="facts" />
      </Section>
      <Section v-if="view.sub_projects.length" :title="__('Sub-projects')" :aside="view.sub_projects.length">
        <Rows :rows="view.sub_projects.map((one) => ({ key: one.name, label: one.title || one.name, value: one.status === 'Completed' ? __('Completed') : `${one.share}%`, progress: one.share, route: `/desk/project/${one.name}` }))" />
      </Section>
      <Section v-if="view.subcontracts?.length" :title="__('Subcontracts')" :aside="view.subcontracts.length">
        <Rows :rows="view.subcontracts.map((one) => ({ key: one.order, label: one.supplier, dim: money(one.ordered, said.currency), value: billed(one) >= 100 ? __('Billed') : __('{0}% billed', [billed(one)]), progress: billed(one), route: one.route }))" />
      </Section>
      <Section v-if="view.activities?.length" :title="__('By Activity')" :aside="__('This month')">
        <Rows :rows="view.activities.map((one) => ({ key: one.activity, label: one.activity, dim: one.amount ? money(one.amount, said.currency) : '', value: hours(one.hours) }))" />
      </Section>
      <Section v-if="view.people?.length" :title="__('Who Logged Time')" :aside="__('This month')">
        <Rows :rows="view.people.map((one) => ({ key: one.user, label: one.name, value: hours(one.hours), avatar: one.name }))" />
      </Section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Badge, Button, Textarea } from "frappe-ui";
import { BarChart } from "frappe-ui/charts";

import { Facts, Figures, Rows, Section, __, call, date, go, hours, money, onedesk, setValue } from "../kit";
import { HEALTH } from "./colors";
import Milestones from "./Milestones.vue";
import Months from "./Months.vue";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const view = computed(() => props.said.overview);
const HEALTHS = ["On Track", "At Risk", "Off Track"];

const updates = ref([]);
const loadUpdates = async () => (updates.value = await call("onedesk.one_project.view.updates", { project: props.said.name }));
watch(() => [props.said.name, props.said.modified], loadUpdates, { immediate: true });

const health = ref(props.said.health || "On Track");
const note = ref("");
const posting = ref(false);
async function post() {
  if (!note.value.trim()) return;
  posting.value = true;
  try {
    if (health.value !== props.said.health) await setValue("Project", props.said.name, "one_health", health.value);
    await call("onedesk.one_project.updates.post", { project: props.said.name, note: note.value.trim() });
    note.value = "";
    await loadUpdates();
    emit("changed");
  } finally {
    posting.value = false;
  }
}

const NAMES = () => ({
  contract: __("Contract"), cost: __("Cost"), forecast: __("Forecast Margin"), done: __("Done"),
  hours: __("Hours This Month"), unbilled: __("Not Invoiced Yet"), fee: __("Monthly Fee"), invoiced: __("Invoiced"),
  budget: __("Budget Used"), spent: __("Spent"), due: __("Due"),
});
const figure = (card) => {
  if (card.money !== undefined) return money(card.money, props.said.currency);
  if (card.hours !== undefined) return hours(card.hours);
  if (card.date) return card.value ? date(card.value) : "–";
  return card.value ?? "–";
};
const figures = computed(() =>
  props.said.cards.map((card) => ({
    title: NAMES()[card.key] || card.key,
    value: figure(card),
    note: card.note || (card.note_money ? card.note_money.map(([text, values]) => text.replace(/\{(\d+)\}/g, (_, i) => money(values[Number(i)], props.said.currency))).join(" · ") : ""),
    bar: card.bar,
    alarm: card.tone === "alarm",
  }))
);

const frm = () => ({ doctype: "Project", doc: { name: props.said.name, project_name: props.said.title, customer: props.said.customer }, reload_doc: () => emit("changed") });
const needs = computed(() =>
  view.value.needs.map((one, i) => ({
    key: i,
    dot: one.tone,
    label: one.text,
    sub: one.dim,
    value: one.late ? __("{0} days late", [one.late]) : one.money !== undefined && one.money !== null ? money(one.money, props.said.currency) : "",
    route: one.route,
    onClick:
      one.action === "invoice_time"
        ? () => onedesk().project.invoice_time(frm())
        : one.action === "invoice_month"
          ? () => onedesk().project.invoice_month(frm(), one.month)
          : undefined,
  }))
);

const weekly = computed(() => {
  const w = view.value.weekly;
  return w ? w.labels.map((week, i) => ({ week, hours: w.values[i] })) : [];
});

const facts = computed(() => {
  const s = props.said;
  const retention = view.value.retention;
  return [
    s.customer && { label: __("Customer"), value: s.customer_name || s.customer, route: `/desk/customer/${s.customer}` },
    s.manager && { label: __("Manager"), value: s.manager_name || s.manager },
    s.contract && { label: __("Contract"), value: s.contract, route: `/desk/sales-order/${s.contract}` },
    retention?.one_retention && {
      label: __("Retention"),
      value: retention.one_retention_due ? __("{0}% until {1}", [retention.one_retention, date(retention.one_retention_due)]) : `${retention.one_retention}%`,
    },
    s.starts && { label: __("Starts"), value: date(s.starts) },
    s.ends && { label: __("Ends"), value: date(s.ends) },
    s.parent && { label: __("Part Of"), value: s.parent_title || s.parent, route: `/desk/project/${s.parent}` },
  ].filter(Boolean);
});
const billed = (one) => (one.ordered ? Math.round((100 * one.billed) / one.ordered) : 0);
</script>
