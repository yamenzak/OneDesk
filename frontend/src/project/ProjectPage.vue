<template>
  <Page>
    <Loading v-if="!said" />
    <template v-else>
      <Title :title="said.title" :badges="badges" :line="line" :people="said.team" />
      <Figures :figures="figures" />

      <Tabs v-model="tab" class="mt-2">
        <TabList>
          <TabTrigger value="overview" :label="__('Overview')" />
        </TabList>
        <TabPanel value="overview">
          <div class="grid gap-x-10 pt-2 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
            <div class="min-w-0">
              <Section v-if="view.milestones?.length" :title="__('Milestones')">
                <Milestones :milestones="view.milestones" />
              </Section>
              <Section :title="__('Needs You')" :aside="view.needs.length || ''">
                <Rows :rows="needs" :empty="__('Nothing needs you')" />
              </Section>
              <Section v-if="weekly.length" :title="__('Hours by Week')" :aside="hours(view.weekly.total)">
                <div class="h-56">
                  <BarChart :data="weekly" x="week" :y="['hours']" :series-config="{ hours: { label: __('Hours') } }" />
                </div>
              </Section>
              <Section v-if="view.activities?.length" :title="__('By Activity')" :aside="__('This month')">
                <Rows :rows="view.activities.map((one) => ({ key: one.activity, label: one.activity, dim: one.amount ? money(one.amount) : '', value: hours(one.hours) }))" />
              </Section>
              <Section v-if="view.update" :title="__('Latest Update')">
                <div class="rounded-lg bg-surface-gray-1 px-4 py-3 text-base leading-relaxed">
                  <div class="mb-1 flex justify-between font-medium text-ink-gray-8">
                    <span>{{ view.update.by }}</span><span class="font-normal text-ink-gray-5">{{ date(view.update.on) }}</span>
                  </div>
                  <div class="text-ink-gray-7">{{ view.update.said }}</div>
                </div>
              </Section>
            </div>
            <div class="min-w-0">
              <Section :title="__('About')">
                <Facts :facts="facts" />
              </Section>
              <Section v-if="view.sub_projects.length" :title="__('Sub-projects')" :aside="view.sub_projects.length">
                <Rows :rows="view.sub_projects.map((one) => ({ key: one.name, label: one.title || one.name, value: one.status === 'Completed' ? __('Completed') : `${one.share}%`, progress: one.share, route: `/desk/project/${one.name}` }))" />
              </Section>
              <Section v-if="view.subcontracts?.length" :title="__('Subcontracts')" :aside="view.subcontracts.length">
                <Rows :rows="view.subcontracts.map((one) => ({ key: one.order, label: one.supplier, dim: money(one.ordered), value: billed(one) >= 100 ? __('Billed') : __('{0}% billed', [billed(one)]), progress: billed(one), route: one.route }))" />
              </Section>
              <Section v-if="view.people?.length" :title="__('Who Logged Time')" :aside="__('This month')">
                <Rows :rows="view.people.map((one) => ({ key: one.user, label: one.name, value: hours(one.hours), avatar: one.name }))" />
              </Section>
            </div>
          </div>
        </TabPanel>
      </Tabs>
    </template>
  </Page>
</template>

<script setup>
// A project's page (docs/PROJECT-PAGE.md): what one_project/view.py `said`
// gives, read as the reader. Desk draws the head from what this reports: the
// name, the status, and the actions (onedesk.island_page). The actions open
// desk's own dialogs, in project_actions.js and progress.js.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { TabList, TabPanel, Tabs, TabTrigger } from "frappe-ui";
import { BarChart } from "frappe-ui/charts";

import { Facts, Figures, Loading, Page, Rows, Section, Title, __, call, can, date, follow, go, hours, listen, money, newDoc, onedesk } from "../kit";
import Milestones from "./Milestones.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  onTitle: Function,
  onStatus: Function,
  onActions: Function,
});

const said = ref(null);
const tab = ref("overview");
const name = computed(() => props.route[0]);
const view = computed(() => said.value?.overview || {});

let stop = [];
async function load() {
  const asked = name.value;
  if (!asked) return;
  const got = await call("onedesk.one_project.view.said", { project: asked });
  if (asked !== name.value) return;
  said.value = got;
  report();
}

watch(
  name,
  (now) => {
    stop.forEach((one) => one());
    said.value = null;
    if (!now) return;
    stop = [
      follow("Project", now, load),
      listen("one_project_money", (data) => data.project === now && load()),
    ];
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => stop.forEach((one) => one()));

// The project as desk's shared actions take it (project_actions.js).
const frm = () => ({
  doctype: "Project",
  doc: { name: said.value.name, project_name: said.value.title, customer: said.value.customer },
  reload_doc: load,
});
const desk = onedesk;

function report() {
  const s = said.value;
  props.onTitle?.(s.title);
  props.onStatus?.({ label: __(s.status), color: { Open: "blue", Completed: "green", Cancelled: "gray" }[s.status] || "gray" });
  props.onActions?.(actions(s));
}

// What can be done to the project, each only for whoever may do it.
function actions(s) {
  const list = [];
  const main = mainAction(s);
  if (main) list.push({ ...main, primary: true });
  if (can("read", "Task")) {
    list.push({ label: __("Board"), button: true, onClick: () => desk().project.board(frm()) });
    list.push({ label: __("Schedule"), button: true, onClick: () => desk().project.plan(frm()) });
  }
  list.push({ label: __("Edit Details"), onClick: () => go(`/desk/project/${encodeURIComponent(s.name)}?edit=1`) });
  if (main?.key !== "post") list.push({ label: __("Post Update"), onClick: () => desk().project.post(frm()) });
  if (s.customer && can("create", "Quotation"))
    list.push({
      label: __("Quote Extra Work"),
      onClick: () => newDoc("Quotation", { project: s.name, one_extra_work: 1, quotation_to: "Customer", party_name: s.customer }),
    });
  if (s.can_write) list.push({ label: __("Group Under New Project"), onClick: () => desk().project.group(frm()) });
  if (can("create", "Project Template")) list.push({ label: __("Save as Template"), onClick: () => desk().project.save_as(frm()) });
  return list;
}

// What a project of this kind is mostly opened to do.
function mainAction(s) {
  if (s.kind === "Fixed Price" && s.contract && can("create", "Sales Invoice"))
    return { key: "bill", label: __("Bill Progress"), onClick: () => desk().progress.ask({ doctype: "Sales Order", doc: { name: s.contract } }) };
  if (s.kind === "Time and Materials" && s.customer && can("create", "Sales Invoice"))
    return { key: "invoice_time", label: __("Invoice Time"), onClick: () => desk().project.invoice_time(frm()) };
  return { key: "post", label: __("Post Update"), onClick: () => desk().project.post(frm()) };
}

const badges = computed(() => {
  const s = said.value;
  const health = { "On Track": "green", "At Risk": "amber", "Off Track": "red" };
  return [{ label: __(s.kind) }, s.health && { label: __(s.health), theme: health[s.health] }].filter(Boolean);
});

const line = computed(() => {
  const s = said.value;
  const dates = [s.starts, s.ends].filter(Boolean).map(date).join(" – ");
  return [
    s.parent && { label: s.parent_title || s.parent, route: `/desk/project/${s.parent}` },
    s.customer && { label: s.customer_name || s.customer, route: `/desk/customer/${s.customer}` },
    dates && { label: dates },
    s.manager_name && { label: s.manager_name },
  ].filter(Boolean);
});

const NAMES = () => ({
  contract: __("Contract"), cost: __("Cost"), forecast: __("Forecast Margin"), done: __("Done"),
  hours: __("Hours This Month"), unbilled: __("Not Invoiced Yet"), fee: __("Monthly Fee"), invoiced: __("Invoiced"),
  budget: __("Budget Used"), spent: __("Spent"), due: __("Due"),
});

const figures = computed(() =>
  said.value.cards.map((card) => ({
    title: NAMES()[card.key] || card.key,
    value: figure(card),
    note: card.note || (card.note_money ? card.note_money.map(([text, values]) => text.replace(/\{(\d+)\}/g, (_, i) => money(values[Number(i)], said.value.currency))).join(" · ") : ""),
    bar: card.bar,
    alarm: card.tone === "alarm",
  }))
);

function figure(card) {
  if (card.money !== undefined) return money(card.money, said.value.currency);
  if (card.hours !== undefined) return hours(card.hours);
  if (card.date) return card.value ? date(card.value) : "–";
  return card.value ?? "–";
}

const needs = computed(() =>
  view.value.needs.map((one, i) => ({
    key: i,
    dot: one.tone,
    label: one.text,
    sub: one.dim,
    value: one.late ? __("{0} days late", [one.late]) : one.money !== undefined && one.money !== null ? money(one.money, said.value.currency) : "",
    route: one.route,
    onClick: one.action === "invoice_time" ? () => desk().project.invoice_time(frm()) : undefined,
  }))
);

const weekly = computed(() => {
  const w = view.value.weekly;
  return w ? w.labels.map((week, i) => ({ week, hours: w.values[i] })) : [];
});

const facts = computed(() => {
  const s = said.value;
  const retention = view.value.retention;
  return [
    { label: __("Kind"), value: __(s.kind) },
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
