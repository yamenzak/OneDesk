<template>
  <!-- What the project is and how it is going, laid out for its kind
       (docs/PROJECT-PAGE.md): its figures and what the kind is worked by on
       the left; what needs someone and the facts on the right. Each thing is
       in one place. -->
  <div class="grid gap-x-10 pb-12 pt-2 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <Section v-if="said.notes" :title="__('Brief')" :action="said.can_write ? { icon: 'lucide-pencil', label: __('Edit Brief'), onClick: editBrief } : null">
        <div class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.notes" />
      </Section>

      <Section :title="__('Numbers')">
        <Figures :figures="figures" />
      </Section>

      <template v-if="kind === 'Fixed Price'">
        <Section v-if="view.billing" :title="__('Work and Billing')">
          <Rows :rows="workAndBilling" />
          <Button v-if="view.billing.unbilled && said.contract && can('create', 'Sales Invoice')" class="mt-3" :label="__('Bill Progress')" @click="onedesk().project.bill_progress(said.orders, said.contract, said.currency, view.billing.billable?.share)" />
        </Section>
        <Section :title="__('Budget')" :aside="view.budget.count > view.budget.lines.length ? __('{0} cost types', [view.budget.count]) : ''" :action="said.views?.includes('money') ? { icon: 'lucide-arrow-up-right', label: __('Money'), onClick: () => $emit('view', 'money') } : null">
          <Rows :rows="budget" :empty="__('No cost types')" />
        </Section>
        <Section :title="__('Milestones')">
          <Milestones v-if="view.milestones.list.length" :milestones="view.milestones.list" />
          <div v-else class="py-3 text-base text-ink-gray-5">{{ __("No milestones") }}</div>
          <Button v-if="can('create', 'Task')" class="mt-3" icon-left="lucide-plus" :label="__('Add Milestone')" @click="onedesk().project.add_milestone(view.milestones.projects, kind === 'Fixed Price', () => emit('changed'))" />
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
        <Section v-if="view.months" :title="__('Months')" :aside="__('{0} a month', [money(view.months.fee, view.months.currency)])">
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
        <Section :title="__('Milestones')">
          <Milestones v-if="view.milestones.list.length" :milestones="view.milestones.list" />
          <div v-else class="py-3 text-base text-ink-gray-5">{{ __("No milestones") }}</div>
          <Button v-if="can('create', 'Task')" class="mt-3" icon-left="lucide-plus" :label="__('Add Milestone')" @click="onedesk().project.add_milestone(view.milestones.projects, kind === 'Fixed Price', () => emit('changed'))" />
        </Section>
        <Section :title="__('Due Soon')" :aside="__('Next 2 weeks')">
          <Rows :rows="view.due_soon.map((one) => ({ key: one.name, label: one.subject, sub: one.who, value: shortDate(one.due), route: `/desk/task/${one.name}` }))" :empty="__('Nothing due')" />
        </Section>
      </template>

      <Section v-if="view.quotes?.length" :title="__('Quotations')">
        <Rows :rows="view.quotes.map((one) => ({ key: one.name, label: one.name, sub: one.extra ? __('Extra Work') : '', dot: QUOTE[one.status] || 'gray', dim: `${__(one.status)} · ${date(one.date)}`, value: money(one.value, one.currency), route: `/desk/quotation/${one.name}` }))" />
      </Section>
      <Section :title="__('Updates')" :aside="said.asking">
        <Updates :said="said" :writing="writing" @changed="$emit('changed')" />
      </Section>
    </div>

    <div class="min-w-0">
      <Section :title="__('Needs You')" :aside="view.needs_count || ''">
        <Rows :rows="needs" :empty="__('Nothing needs you')" />
        <Button v-if="view.needs_all" variant="ghost" class="mt-2 -ms-2" :label="__('Show All')" @click="go(view.needs_all)" />
      </Section>

      <template v-if="kind === 'Fixed Price'">
        <Section v-if="view.subcontracts?.length" :title="__('Subcontracts')" :aside="view.subcontracts_count" :action="said.views?.includes('suppliers') ? { icon: 'lucide-arrow-up-right', label: __('Suppliers'), onClick: () => $emit('view', 'suppliers') } : null">
          <Rows :rows="subcontracts" />
          <Button v-if="view.subcontracts_count > view.subcontracts.length && said.views?.includes('suppliers')" variant="ghost" class="mt-2 -ms-2" :label="__('Show All')" @click="$emit('view', 'suppliers')" />
        </Section>
        <Section v-if="said.orders?.length > 1" :title="__('Orders')" :aside="said.orders.length" :action="{ icon: 'lucide-arrow-up-right', label: __('Orders'), onClick: () => go(said.orders_route) }">
          <Rows :rows="orders" />
          <Button v-if="said.orders.length > orders.length" variant="ghost" class="mt-2 -ms-2" :label="__('Show All')" @click="go(said.orders_route)" />
        </Section>
        <Section v-if="view.retention" :title="__('Retention')" :action="said.views?.includes('money') ? { icon: 'lucide-arrow-up-right', label: __('Money'), onClick: () => $emit('view', 'money') } : null">
          <Rows :rows="retention" />
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

      <Section :title="__('About', null, 'Project')" :action="said.can_write ? { icon: 'lucide-pencil', label: __('Edit About'), onClick: editAbout } : null">
        <Facts :facts="facts" />
        <Button v-if="!said.notes && said.can_write" variant="ghost" class="mt-3 -ms-2" icon-left="lucide-plus" :label="__('Add Brief')" @click="editBrief" />
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

const props = defineProps({ said: { type: Object, required: true }, writing: Boolean });
const emit = defineEmits(["changed", "view"]);
const view = computed(() => props.said.overview);
const kind = computed(() => props.said.kind);

// A quotation's status as a dot: still open, ordered, or gone.
const QUOTE = { Open: "blue", Replied: "blue", "Partially Ordered": "green", Ordered: "green", Lost: "red", Expired: "orange", Draft: "gray" };

const NAMES = () => ({
  contract: __("Contract"), quoted: __("Quoted"), valid: __("Valid Till"), billed: __("Billed"), cost: __("Cost"), forecast: __("Forecast Margin"), done: __("Done"),
  hours: __("Hours This Month"), month: __("This Month"), unbilled: __("Not Invoiced Yet"), fee: __("Monthly Fee"),
  months_waiting: __("Months Not Invoiced"), invoiced: __("Invoiced"), budget: __("Budget Used"), due: __("Due"), overdue: __("Overdue Tasks"),
});
const figure = (card) => {
  if (card.money !== undefined) return money(card.money, card.currency || props.said.currency);
  if (card.hours !== undefined) return hours(card.hours);
  if (card.date) return card.value ? date(card.value) : "–";
  return card.value ?? "–";
};
const figures = computed(() =>
  props.said.cards.map((card) => ({
    title: NAMES()[card.key] || card.key,
    value: figure(card),
    note: card.note || (card.note_money ? card.note_money.map(([text, values]) => text.replace(/\{(\d+)\}/g, (_, i) => money(values[Number(i)], props.said.currency))).join("\n") : ""),
    bar: card.bar,
    alarm: card.tone === "alarm",
    route: card.route,
    action: opens(card),
    button: next(card),
  }))
);
// The work done beside what's billed and paid, as amounts (view.work_and_billing).
const workAndBilling = computed(() => {
  const b = view.value.billing;
  const sum = (value) => money(value, props.said.currency);
  const owed = [b.overdue && __("{0} overdue", [sum(b.overdue)]), b.retention && __("{0} retention", [sum(Math.min(b.retention, b.owed))])].filter(Boolean);
  return [
    { key: "done", label: __("Work Done"), progress: b.done, value: `${b.done}%` },
    b.billable && { key: "billable", label: __("Billable on Milestones"), dim: b.billable.names.join(", "), progress: b.billable.share, value: `${b.billable.share}%` },
    b.unbilled && { key: "unbilled", label: __("Not Invoiced Yet"), value: sum(b.unbilled) },
    b.ahead && { key: "ahead", label: b.billable ? __("Billed Ahead of the Milestones") : __("Billed Ahead of the Work"), value: sum(b.ahead) },
    b.owed && { key: "owed", label: __("Owed"), dim: owed.join(" · "), value: sum(b.owed), dot: b.overdue ? "red" : undefined },
    b.advance && { key: "advance", label: __("Paid in Advance"), value: sum(b.advance) },
    b.last && { key: "last", label: __("Last Billed"), dim: b.last.share !== null ? __("{0}% billed", [b.last.share]) : "", value: date(b.last.date) },
  ].filter(Boolean);
});

// Each cost type over the project and those under it, then Other for the
// rest, so the rows add up to Numbers (view._budget_lines).
const budget = computed(() => {
  const b = view.value.budget;
  const sum = (value) => money(value, props.said.currency);
  const row = (one, key, label) => {
    const used = one.spent + one.committed;
    const whole = Math.max(one.budget, used) || 1;
    return {
      key,
      label,
      dim: [
        one.spent && __("{0} spent", [sum(one.spent)]),
        one.committed && __("{0} on order", [sum(one.committed)]),
        one.budget && __("{0} budget", [sum(one.budget)]),
      ].filter(Boolean).join(" · "),
      progress: one.budget ? Math.round((100 * one.spent) / whole) : null,
      then: one.budget ? Math.round((100 * one.committed) / whole) : null,
      value: !one.budget ? sum(used) : one.left < 0 ? __("{0} over", [sum(-one.left)]) : __("{0} left", [sum(one.left)]),
      dot: one.budget && one.left < 0 ? "red" : undefined,
    };
  };
  return [...b.lines.map((one) => row(one, one.cost_type, one.cost_type)), b.other && row(b.other, "other", __("Other"))].filter(Boolean);
});

// A figure whose documents are a view of this page opens that view.
const opens = (card) =>
  card.view && !card.route && props.said.views?.includes(card.view)
    ? { icon: "lucide-arrow-up-right", label: NAMES()[card.key] || card.key, onClick: () => emit("view", card.view) }
    : null;
// What the first figure asks for next, for whoever may do it.
const next = (card) => {
  if (!can("create", "Sales Order")) return null;
  if (card.action === "add_contract" && props.said.can_write && props.said.customer)
    return { label: __("Add Contract"), icon: "lucide-plus", onClick: () => onedesk().project.add_contract(frm()) };
  return null;
};

const frm = () => ({ doctype: "Project", doc: { name: props.said.name, project_name: props.said.title, customer: props.said.customer }, reload_doc: () => emit("changed") });
const needs = computed(() =>
  view.value.needs.map((one, i) => ({
    key: i,
    dot: one.tone,
    label: one.text,
    below: one.dim,
    value: one.today ? __("Today") : one.late === 1 ? __("1 day late") : one.late ? __("{0} days late", [one.late]) : one.money !== undefined && one.money !== null ? money(one.money, props.said.currency) : "",
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

// What the head doesn't say: how progress is measured, when it's due and how
// far off that is, who's on it and how much it matters. The head has the
// customer, the order, the dates and the manager; the breadcrumb has where
// a sub-project sits.
const facts = computed(() => {
  const s = props.said;
  const left = s.days_left;
  const open = s.status === "Open";
  return [
    s.progress_method && { label: __("Progress"), value: __(s.progress_method) },
    s.kind !== "Internal" && {
      label: __("Due"),
      value: s.ends ? [date(s.ends), open && ends(left)].filter(Boolean).join(" · ") : __("Not set"),
      tone: !s.ends ? "gray" : open && left < 0 ? "red" : undefined,
    },
    s.team?.length && { label: __("Team"), value: s.team.length === 1 ? __("1 person") : __("{0} people", [s.team.length]), avatars: s.team.map((one) => ({ label: one.name, image: one.image })), onClick: () => emit("view", "team") },
    s.priority && { label: __("Priority"), value: __(s.priority) },
  ].filter(Boolean);
});
function ends(left) {
  if (left === null || left === undefined) return "";
  if (left === -1) return __("1 day late");
  if (left < 0) return __("{0} days late", [-left]);
  if (left === 0) return __("Today");
  return left === 1 ? __("Tomorrow") : __("In {0} days", [left]);
}
const editAbout = () => onedesk().project.edit_about(props.said.name, props.said.modified, () => emit("changed"));
const editBrief = () => onedesk().project.edit_brief(props.said.name, props.said.modified, () => emit("changed"));
// What the customer holds and what's held from suppliers, each with its rate
// when the orders agree and when the first of it is due (retention.sides).
const retention = computed(() =>
  [
    ["customer", __("From the Customer")],
    ["suppliers", __("To Suppliers")],
  ]
    .filter(([key]) => view.value.retention[key])
    .map(([key, label]) => {
      const one = view.value.retention[key];
      return {
        key,
        label,
        below: [one.percent !== null && `${one.percent}%`, __("Due {0}", [date(one.due)])].filter(Boolean).join(" · "),
        value: money(one.held, props.said.currency),
      };
    })
);
// As many as the other sections show (view.SHOWN).
const SHOWN = 8;
// The customer's orders across the tree: where each is and what it's for,
// what's left to bill, and ERPNext's status when it can't be billed.
const orders = computed(() =>
  props.said.orders.slice(0, SHOWN).map((one) => ({
    key: one.name,
    label: one.name,
    badge: one.extra ? __("Extra Work") : undefined,
    lines: [
      [one.where, one.for].filter(Boolean).join(" · "),
      [money(one.value, props.said.currency), one.billed > 0 && one.billed < 100 && __("{0} left", [money(one.left, props.said.currency)])].filter(Boolean).join(" · "),
    ].filter(Boolean),
    value: one.billed >= 100 ? __("Billed") : one.billable ? __("{0}% billed", [one.billed]) : __(one.status),
    route: `/desk/sales-order/${one.name}`,
  }))
);
const billed = (one) => (one.ordered ? Math.round((100 * one.billed) / one.ordered) : 0);
// Each order: what it's for and where, how far it's billed, and when that's
// ahead of the work on its project, or there's something to pay.
const subcontracts = computed(() =>
  view.value.subcontracts.map((one) => {
    const ahead = one.done !== null && one.done !== undefined && billed(one) > one.done;
    return {
      key: one.order,
      label: one.supplier,
      lines: [
        [one.where, one.for].filter(Boolean).join(" · "),
        [money(one.ordered, props.said.currency), ahead && __("{0}% done", [one.done])].filter(Boolean).join(" · "),
        one.to_pay >= 1 && __("{0} to pay", [money(one.to_pay, props.said.currency)]),
      ].filter(Boolean),
      value: billed(one) >= 100 ? __("Billed") : __("{0}% billed", [billed(one)]),
      dot: ahead ? "orange" : undefined,
      route: one.route,
    };
  })
);
</script>
