<template>
  <!-- What the project is and how it is going, laid out for its kind
       (docs/PROJECT-PAGE.md): its figures, two to a row in cards, its tasks
       and hours as charts, and what the kind is worked by on the left; what
       needs someone, in a card, and the facts on the right. A group of cards
       is its own divide, so no rule runs above or below one. Each thing is
       in one place. -->
  <div ref="root" class="grid gap-x-10 pb-12 pt-2 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
    <div class="min-w-0">
      <div data-cards class="py-5">
        <Figures :figures="figures" boxed :columns="figures.length === 4 ? 2 : figures.length" />
      </div>

      <Section v-if="said.notes" :title="__('Brief')" :action="said.can_write ? { icon: 'lucide-pencil', label: __('Edit Brief'), onClick: editBrief } : null">
        <div class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="said.notes" />
      </Section>

      <div v-if="taskSlices.length || weekly.length" data-cards class="grid gap-3 pb-5 pt-1" :class="{ 'sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]': taskSlices.length && weekly.length }">
        <ChartCard v-if="taskSlices.length" class="h-64">
          <DonutChart :title="__('Tasks')" :subtitle="tasksSaid" :data="taskSlices" category="status" value="n" :center-label="tasks.length === 1 ? tasks[0].status : __('Tasks')" :palette="taskColors" @select="$emit('view', 'tasks')" />
        </ChartCard>
        <ChartCard v-if="weekly.length" class="h-64">
          <BarChart :title="__('Hours by Week')" :subtitle="__('{0} in 12 weeks', [hours(view.weekly.total)])" :data="weekly" x="week" :y="['hours']" :series-config="{ hours: { label: __('Hours') } }" />
        </ChartCard>
      </div>

      <template v-if="kind === 'Fixed Price'">
        <Section v-if="view.billing" :title="__('Work and Billing')">
          <Rows :rows="workAndBilling" />
          <Button v-if="view.billing.unbilled && said.contract && can('create', 'Sales Invoice')" class="mt-3" :label="__('Bill Progress')" @click="onedesk().project.bill_progress(said.orders, said.contract, said.currency, view.billing.billable?.share)" />
        </Section>
        <Section :title="__('Budget')" :aside="view.budget.count > view.budget.lines.length ? __('{0} cost types', [view.budget.count]) : ''" :action="said.views?.includes('money') ? { icon: 'lucide-arrow-up-right', label: __('Money'), onClick: () => $emit('view', 'money') } : null">
          <ChartCard v-if="budgetBars.length" :style="{ height: `${5.5 + 2.25 * budgetBars.length}rem` }">
            <BarChart :data="budgetBars" x="type" :y="['spent', 'committed', 'left']" horizontal stacked :series-config="budgetSeries" :y-axis="{ format: (value) => money(value, said.currency) }" />
          </ChartCard>
          <div v-else class="py-3 text-base text-ink-gray-5">{{ __("No cost types") }}</div>
          <Rows v-if="over.length" class="mt-2" :rows="over" />
        </Section>
        <Section :title="__('Milestones')">
          <Milestones v-if="view.milestones.list.length" :milestones="view.milestones.list" />
          <div v-else class="py-3 text-base text-ink-gray-5">{{ __("No milestones") }}</div>
          <Button v-if="can('create', 'Task')" class="mt-3" icon-left="lucide-plus" :label="__('Add Milestone')" @click="onedesk().project.add_milestone(view.milestones.projects, kind === 'Fixed Price', () => emit('changed'))" />
        </Section>
      </template>

      <template v-else-if="kind === 'Time and Materials'">
        <Section :title="__('Not Invoiced Yet')" :aside="unbilledTotal">
          <Rows :rows="view.unbilled.map((one) => ({ key: one.name, label: one.name, avatar: one.name, dim: hours(one.hours), value: money(one.amount, said.currency) }))" :empty="__('All time is invoiced')" />
          <Button v-if="view.unbilled.length && said.customer && can('create', 'Sales Invoice')" class="mt-3" :label="__('Invoice Time')" @click="onedesk().project.invoice_time(frm())" />
        </Section>
      </template>

      <template v-else-if="kind === 'Retainer'">
        <Section v-if="view.months" :title="__('Months')" :aside="__('{0} a month', [money(view.months.fee, view.months.currency)])">
          <Months :months="view.months" @invoice="(month) => onedesk().project.invoice_month(frm(), month)" />
        </Section>
      </template>

      <template v-else>
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
      <Section boxed :title="__('Needs You')" :aside="view.needs_count || ''">
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
      <Section v-if="view.sub_projects.count" :title="__('Sub-projects')" :aside="view.sub_projects.count">
        <Rows :rows="subProjects" />
        <Button v-if="view.sub_projects.all" variant="ghost" class="mt-2 -ms-2" :label="__('Show All')" @click="go(view.sub_projects.all)" />
        <Button v-if="canAddSub" variant="ghost" class="mt-2 -ms-2" icon-left="lucide-plus" :label="__('Add Sub-project')" @click="addSub" />
      </Section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { BarChart, ChartCard, DonutChart, useChartTokens } from "frappe-ui/charts";

import { Facts, Figures, Rows, Section, __, can, colors, date, go, hours, money, newDoc, onedesk, shortDate } from "../kit";
import Milestones from "./Milestones.vue";
import Months from "./Months.vue";
import Updates from "./Updates.vue";

const props = defineProps({ said: { type: Object, required: true }, writing: Boolean });
const emit = defineEmits(["changed", "view"]);
const view = computed(() => props.said.overview);
// The charts' colours, as frappe-ui reads them for this island and its theme.
const root = ref();
const { tokens } = useChartTokens(root);
const kind = computed(() => props.said.kind);

// A quotation's status as a dot: still open, ordered, or gone.
const QUOTE = { Open: "blue", Replied: "blue", "Partially Ordered": "green", Ordered: "green", Lost: "red", Expired: "orange", Draft: "gray" };

const NAMES = () => ({
  contract: __("Contract"), quoted: __("Quoted"), valid: __("Valid Till"), billed: __("Billed"), cost: __("Cost"), forecast: __("Forecast Margin"), done: __("Done"),
  hours: __("Hours This Month"), month: __("This Month"), unbilled: __("Not Invoiced Yet"), fee: __("Monthly Fee"),
  months_waiting: __("Months Not Invoiced"), invoiced: __("Invoiced"), budget: __("Budget Used"), due: __("Due"), overdue: __("Overdue Tasks"),
});
const figure = (card) => {
  if (card.money !== undefined && card.money !== null) return money(card.money, card.currency || props.said.currency);
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
// rest, so the bars add up to the figures (view._budget_lines): what's
// spent, what's on order, and what's left of its budget. A cost type over
// its budget is a row under the chart, as a red figure is.
const budgetLines = computed(() => {
  const b = view.value.budget;
  return [...b.lines.map((one) => ({ ...one, type: one.cost_type })), b.other && { ...b.other, type: __("Other") }].filter(Boolean);
});
const budgetBars = computed(() =>
  budgetLines.value.map((one) => ({ type: one.type, spent: one.spent, committed: one.committed, left: Math.max(one.left || 0, 0) }))
);
// Spent and on order are one hue at two strengths; what's left is the track.
const budgetSeries = computed(() => {
  const [spent, committed] = tokens.value.categorical;
  return { spent: { label: __("Spent"), color: spent }, committed: { label: __("On Order"), color: committed }, left: { label: __("Left"), color: tokens.value.axisLine } };
});
const over = computed(() =>
  budgetLines.value
    .filter((one) => one.budget && one.left < 0)
    .map((one) => ({ key: one.type, dot: "red", label: one.type, below: __("{0} budget", [money(one.budget, props.said.currency)]), value: __("{0} over", [money(-one.left, props.said.currency)]) }))
);

// The tasks by status, in the colours their badges have: Completed, Working,
// Pending Review and Overdue in the ramp's green, blue, amber and red, Open,
// not started, in gray. The ring draws the largest first, so the colours are
// listed in that order too.
const TASK_ORDER = ["Completed", "Working", "Pending Review", "Overdue", "Open"];
const tasks = computed(() =>
  TASK_ORDER.filter((status) => view.value.statuses?.[status])
    .map((status) => ({ key: status, status: __(status), n: view.value.statuses[status] }))
    .sort((a, b) => b.n - a.n)
);
const taskSlices = computed(() => tasks.value.map(({ status, n }) => ({ status, n })));
const taskColors = computed(() => {
  const ramp = tokens.value.categorical;
  const tone = { Completed: ramp[2], Working: ramp[0], "Pending Review": ramp[6], Overdue: ramp[8], Open: colors(root.value, "--outline-gray-3")[0] };
  return tasks.value.map((one) => tone[one.key]);
});
const tasksSaid = computed(() => {
  const all = Object.values(view.value.statuses || {}).reduce((a, b) => a + b, 0);
  return __("{0} of {1} done", [view.value.statuses?.Completed || 0, all]);
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
// far off that is, who's on it, how much it matters and how its time is
// counted. The head has the
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
    s.people?.length && { label: __("Team"), value: s.people.length === 1 ? __("1 person") : __("{0} people", [s.people.length]), avatars: s.people.map((one) => ({ label: one.name, image: one.image })), onClick: () => emit("view", "team") },
    s.priority && { label: __("Priority"), value: __(s.priority) },
    s.time && { label: __("Time"), value: [__(s.time), s.site].filter(Boolean).join(" · ") },
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
// Each sub-project: how it's going (kind, when it's due, who runs it), its
// branch's money by kind, and a dot when it's late, over budget or not on
// track (view._sub_projects).
const subProjects = computed(() =>
  view.value.sub_projects.list.map((one) => {
    const late = one.days_left !== null && one.days_left !== undefined && one.days_left < 0;
    const sum = (value) => money(value, props.said.currency);
    const worth = one.ordered
      ? [sum(one.ordered), one.billed && __("{0}% billed", [Math.round((100 * one.billed) / one.ordered)])]
      : one.budget
        ? [__("{0} of {1} budget", [sum(one.spent), sum(one.budget)])]
        : [one.spent && __("{0} spent", [sum(one.spent)])];
    return {
      key: one.name,
      label: one.title || one.name,
      badge: one.extra ? __("Extra Work") : undefined,
      lines: [
        [one.kind && __(one.kind), when(one.days_left), one.manager].filter(Boolean).join(" · "),
        [...worth, one.below && (one.below === 1 ? __("1 sub-project") : __("{0} sub-projects", [one.below]))].filter(Boolean).join(" · "),
      ].filter(Boolean),
      value: one.status === "Completed" ? __("Completed") : `${one.share}%`,
      dot: one.health === "Off Track" || late || one.over ? "red" : one.health === "At Risk" ? "orange" : undefined,
      route: `/desk/project/${encodeURIComponent(one.name)}`,
    };
  })
);
function when(left) {
  if (left === null || left === undefined) return "";
  if (left === -1) return __("1 day late");
  if (left < 0) return __("{0} days late", [-left]);
  if (left === 0) return __("Due today");
  return left === 1 ? __("Due tomorrow") : __("Due in {0} days", [left]);
}
const canAddSub = computed(() => props.said.can_write && can("create", "Project"));
const addSub = () => newDoc("Project", { one_parent: props.said.name, customer: props.said.customer });
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
