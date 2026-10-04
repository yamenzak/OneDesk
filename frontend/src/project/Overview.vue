<template>
  <!-- What the project is and how it is going, laid out for its kind
       (docs/PROJECT-PAGE.md): its figures and what the kind is worked by on
       the left; what needs someone and the facts on the right. Each thing is
       in one place. -->
  <div class="grid gap-x-10 pb-12 pt-2 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <Section v-if="said.notes" :title="__('Brief')">
        <div class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.notes" />
      </Section>

      <Section :title="__('Numbers')">
        <Figures :figures="figures" />
      </Section>

      <template v-if="kind === 'Fixed Price'">
        <Section :title="__('Work and Billing')">
          <Rows :rows="[
            { key: 'done', label: __('Work Done'), progress: view.billing.done, value: `${view.billing.done}%` },
            { key: 'billed', label: __('Billed'), progress: view.billing.billed, value: `${view.billing.billed}%` },
            { key: 'paid', label: __('Paid'), progress: view.billing.paid, value: `${view.billing.paid}%` },
          ]" />
        </Section>
        <Section v-if="view.budget.length" :title="__('Budget')">
          <Rows :rows="view.budget.map((one) => ({ key: one.cost_type, label: one.cost_type, dim: __('{0} of {1}', [money(one.used, said.currency), money(one.budget, said.currency)]), progress: Math.min(100, one.budget ? Math.round((100 * one.used) / one.budget) : 0), value: one.left < 0 ? __('{0} over', [money(-one.left, said.currency)]) : __('{0} left', [money(one.left, said.currency)]), dot: one.left < 0 ? 'red' : undefined }))" />
        </Section>
        <Section v-if="view.milestones?.length" :title="__('Milestones')">
          <Milestones :milestones="view.milestones" />
        </Section>
      </template>

      <template v-else-if="kind === 'Time and Materials'">
        <Section v-if="weekly.length" :title="__('Hours by Week')" :aside="__('{0} in 12 weeks', [hours(view.weekly.total)])">
          <div class="h-56"><BarChart :data="weekly" x="week" :y="['hours']" :series-config="{ hours: { label: __('Hours') } }" /></div>
        </Section>
        <Section :title="__('Not Invoiced Yet')" :aside="unbilledTotal">
          <Rows :rows="view.unbilled.map((one) => ({ key: one.name, label: one.name, avatar: one.name, dim: hours(one.hours), value: money(one.amount, said.currency) }))" :empty="__('All time is invoiced')" />
          <Button v-if="view.unbilled.length && said.customer && can('create', 'Sales Invoice')" class="mt-3" :label="__('Invoice Time')" @click="onedesk().project.invoice_time(frm())" />
        </Section>
      </template>

      <template v-else-if="kind === 'Retainer'">
        <Section v-if="view.months" :title="__('Months')" :aside="__('{0} a month', [money(view.months.fee, said.currency)])">
          <Months :months="view.months" @invoice="(month) => onedesk().project.invoice_month(frm(), month)" />
        </Section>
        <Section v-if="weekly.length" :title="__('Hours by Week')" :aside="__('{0} in 12 weeks', [hours(view.weekly.total)])">
          <div class="h-56"><BarChart :data="weekly" x="week" :y="['hours']" :series-config="{ hours: { label: __('Hours') } }" /></div>
        </Section>
      </template>

      <template v-else>
        <Section v-if="Object.keys(view.statuses).length" :title="__('Tasks')">
          <Statuses :statuses="view.statuses" @open="$emit('view', 'tasks')" />
        </Section>
        <Section v-if="view.milestones?.length" :title="__('Milestones')">
          <Milestones :milestones="view.milestones" />
        </Section>
        <Section :title="__('Due Soon')" :aside="__('Next 2 weeks')">
          <Rows :rows="view.due_soon.map((one) => ({ key: one.name, label: one.subject, sub: one.who, value: shortDate(one.due), route: `/desk/task/${one.name}` }))" :empty="__('Nothing due')" />
        </Section>
      </template>

      <Section :title="__('Updates')">
        <Updates :said="said" @changed="$emit('changed')" />
      </Section>
    </div>

    <div class="min-w-0">
      <Section :title="__('Needs You')" :aside="view.needs.length || ''">
        <Rows :rows="needs" :empty="__('Nothing needs you')" />
      </Section>

      <template v-if="kind === 'Fixed Price'">
        <Section v-if="view.subcontracts?.length" :title="__('Subcontracts')" :aside="view.subcontracts.length">
          <Rows :rows="view.subcontracts.map((one) => ({ key: one.order, label: one.supplier, dim: money(one.ordered, said.currency), value: billed(one) >= 100 ? __('Billed') : __('{0}% billed', [billed(one)]), progress: billed(one), route: one.route }))" />
        </Section>
        <Section v-if="view.retention" :title="__('Retention')">
          <Facts :facts="[
            { label: __('Held'), value: money(view.retention.held, said.currency) },
            { label: __('Rate'), value: `${view.retention.percent}%` },
            view.retention.due && { label: __('Due'), value: date(view.retention.due) },
          ].filter(Boolean)" />
        </Section>
      </template>
      <Section v-if="view.people?.length" :title="__('By Person')" :aside="__('This month')">
        <Rows :rows="view.people.map((one) => ({ key: one.user, label: one.name, value: hours(one.hours), avatar: one.name }))" />
      </Section>
      <Section v-if="view.activities?.length" :title="__('By Activity')" :aside="__('This month')">
        <Rows :rows="view.activities.map((one) => ({ key: one.activity, label: one.activity, dim: one.amount ? money(one.amount, said.currency) : '', value: hours(one.hours) }))" />
      </Section>
      <Section v-if="view.on_it?.length" :title="__('Who\'s On It')">
        <Rows :rows="view.on_it.map((one) => ({ key: one.user, label: one.name, avatar: one.name, value: one.tasks === 1 ? __('1 task') : __('{0} tasks', [one.tasks]) }))" />
      </Section>

      <Section :title="__('About')">
        <Facts :facts="facts" />
        <Button v-if="!said.notes && said.can_write" variant="ghost" class="mt-3 -ms-2" icon-left="lucide-plus" :label="__('Add Brief')" @click="go(`/desk/project/${said.name}?edit=1`)" />
      </Section>
      <Section v-if="view.sub_projects.length" :title="__('Sub-projects')" :aside="view.sub_projects.length">
        <Rows :rows="view.sub_projects.map((one) => ({ key: one.name, label: one.title || one.name, value: one.status === 'Completed' ? __('Completed') : `${one.share}%`, progress: one.share, route: `/desk/project/${one.name}` }))" />
      </Section>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Button } from "frappe-ui";
import { BarChart } from "frappe-ui/charts";

import { Facts, Figures, Rows, Section, __, can, date, go, hours, money, onedesk, shortDate } from "../kit";
import Milestones from "./Milestones.vue";
import Months from "./Months.vue";
import Statuses from "./Statuses.vue";
import Updates from "./Updates.vue";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed", "view"]);
const view = computed(() => props.said.overview);
const kind = computed(() => props.said.kind);

const NAMES = () => ({
  contract: __("Contract"), quoted: __("Quoted"), billed: __("Billed"), cost: __("Cost"), forecast: __("Forecast Margin"), done: __("Done"),
  hours: __("Hours This Month"), month: __("This Month"), unbilled: __("Not Invoiced Yet"), fee: __("Monthly Fee"),
  months_waiting: __("Months Not Invoiced"), invoiced: __("Invoiced"), budget: __("Budget Used"), due: __("Due"), overdue: __("Overdue Tasks"),
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
    route: card.route,
    button: next(card),
  }))
);
// What the first figure asks for next, for whoever may do it.
const next = (card) => {
  if (!can("create", "Sales Order")) return null;
  if (card.action === "add_contract" && props.said.can_write && props.said.customer)
    return { label: __("Add Contract"), icon: "lucide-plus", onClick: () => onedesk().project.add_contract(frm()) };
  if (card.action === "order") return { label: __("Make Order"), icon: "lucide-file-check", onClick: () => onedesk().project.order_quote(card.quotation) };
  return null;
};

const frm = () => ({ doctype: "Project", doc: { name: props.said.name, project_name: props.said.title, customer: props.said.customer }, reload_doc: () => emit("changed") });
const needs = computed(() =>
  view.value.needs.map((one, i) => ({
    key: i,
    dot: one.tone,
    label: one.text,
    sub: one.dim,
    value: one.late ? __("{0} days late", [one.late]) : one.money !== undefined && one.money !== null ? money(one.money, props.said.currency) : "",
    route: one.route,
  }))
);

const weekly = computed(() => {
  const w = view.value.weekly;
  return w ? w.labels.map((week, i) => ({ week, hours: w.values[i] })) : [];
});
const unbilledTotal = computed(() => {
  const all = view.value.unbilled || [];
  return all.length ? money(all.reduce((sum, one) => sum + one.amount, 0), props.said.currency) : "";
});

const facts = computed(() => {
  const s = props.said;
  return [
    s.customer && { label: __("Customer"), value: s.customer_name || s.customer, route: `/desk/customer/${s.customer}` },
    s.manager && { label: __("Manager"), value: s.manager_name || s.manager },
    s.contract && { label: __("Contract"), value: s.contract, route: `/desk/sales-order/${s.contract}` },
    s.starts && { label: __("Starts"), value: date(s.starts) },
    s.ends && { label: __("Ends"), value: date(s.ends) },
    s.parent && { label: __("Part Of"), value: s.parent_title || s.parent, route: `/desk/project/${s.parent}` },
  ].filter(Boolean);
});
const billed = (one) => (one.ordered ? Math.round((100 * one.billed) / one.ordered) : 0);
</script>
