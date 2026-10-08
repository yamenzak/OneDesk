<template>
  <!-- Where the project's money stands and where it's heading: the forecast,
       the customer's side and the cost side, and the budget by cost type.
       Every figure opens the documents behind it (one_project/money.py). -->
  <div class="pb-12">
    <!-- The title, as on Tasks and Time, and the currency every amount is in. -->
    <div class="flex flex-wrap items-center gap-2 pb-2">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-wallet size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Money") }}
      </h2>
      <span v-if="cash.currency" class="text-sm text-ink-gray-5">{{ __("Amounts in {0}", [cash.currency]) }}</span>
      <!-- What the work uses: stock taken out for it, and what the team paid
           themselves, each naming the project (money.py). -->
      <Button v-if="can('create', 'Stock Entry')" size="sm" icon-left="lucide-package-minus" :label="__('Issue Stock')" @click="newDoc('Stock Entry', { stock_entry_type: 'Material Issue', purpose: 'Material Issue', project: said.name })" />
      <Button v-if="can('create', 'Expense Claim')" size="sm" icon-left="lucide-plus" :label="__('New Expense Claim')" @click="newDoc('Expense Claim', { project: said.name })" />
    </div>
    <Section :title="soFarOnly ? __('So Far') : __('Forecast')" icon="lucide-trending-up">
      <Figures :figures="forecast" />
    </Section>

    <div class="grid gap-x-10 border-b border-outline-gray-1 lg:grid-cols-2 [&>section]:border-0">
      <Section v-if="selling" :title="__('Customer')" icon="lucide-user-round">
        <Rows :rows="customer" :empty="__('No sales yet')" />
      </Section>
      <Section :title="__('Cost')" icon="lucide-receipt">
        <Rows :rows="cost" :empty="__('No costs yet')" />
      </Section>
    </div>

    <section class="py-5">
      <div class="mb-3 flex items-center justify-between gap-2">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9"><span class="lucide-layers size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Cost Types") }}</h2>
        <Button v-if="types.can_set" size="sm" icon-left="lucide-plus" :label="__('Add Cost Type')" @click="costType()" />
      </div>
      <div v-if="!types.lines.length" class="py-3 text-base text-ink-gray-5">{{ __("No cost types") }}</div>
      <List v-else :columns="{ base: ['minmax(0,1fr)', '6.5rem', '4rem'], md: ['minmax(0,1.4fr)', '7rem', '7rem', '7rem', '7rem', 'minmax(6rem,1fr)'] }" :row-height="44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Cost Type") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Budget") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Committed") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-md:hidden">{{ __("Spent") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Left") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Used") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="typeRows" row-key="key" v-slot="{ item }">
          <ListRow v-bind="item.key !== 'other' ? { onClick: () => openType(item) } : {}">
            <ListCell class="min-w-0">
              <span class="flex min-w-0 flex-col">
                <span class="truncate text-base" :class="item.key === 'other' ? 'text-ink-gray-6' : 'text-ink-gray-8'">{{ item.cost_type }}</span>
                <span v-if="item.key === 'other'" class="truncate text-sm text-ink-gray-5">{{ __("Not in a cost type") }}</span>
              </span>
            </ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ plain(item.budget) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ plain(item.committed) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ plain(item.spent) }}</ListCell>
            <ListCell class="justify-end tabular-nums" :class="item.left < 0 ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ plain(item.left) }}</ListCell>
            <ListCell class="gap-2">
              <Progress :value="Math.min(100, used(item))" size="md" class="w-full" />
              <span class="w-10 shrink-0 text-end text-sm tabular-nums" :class="used(item) > 100 ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ used(item) }}%</span>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>

    <!-- What was booked to a cost type, each opening its document. -->
    <Dialog v-model:open="showing" :title="opened?.cost_type" size="xl">
      <Loading v-if="!booked" />
      <Rows v-else :rows="booked" :empty="__('Nothing booked yet')" />
      <template #actions>
        <div class="flex justify-end">
          <Button v-if="types.can_set && opened?.account" icon-left="lucide-pencil" :label="__('Change Budget')" @click="(showing = false), costType(opened)" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button, Dialog, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Rows, Section, __, call, can, date, money, newDoc, onedesk, plain } from "../kit";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed", "view"]);

const cash = computed(() => props.said.money);
const amount = (value) => money(value, cash.value.currency);
// Amounts in a table, the currency said once at the top (frappe's own
// number format).
const maybe = (value) => (value === null || value === undefined ? "–" : amount(value));
const share = (part, whole) => (whole ? Math.max(0, Math.min(100, Math.round((100 * part) / whole))) : null);
const percent = (part, whole) => (whole ? Math.round((100 * part) / whole) : null);
const frm = () => ({ doctype: "Project", doc: { name: props.said.name } });

// The forecast, by how the project earns (money.py). A project with no
// customer and nothing ordered by one has no contract: its forecast is the
// budget and what's left of it.
const selling = computed(() => Boolean(props.said.customer || cash.value.contract));
const kind = computed(() => cash.value.kind);
// Time and materials and a retainer have no contract to forecast against.
const soFarOnly = computed(() => selling.value && ["Time and Materials", "Retainer"].includes(kind.value));
const budgetFigure = () => {
  const c = cash.value;
  return {
    title: __("Budget"),
    value: c.budget ? amount(c.budget) : "–",
    note: c.budget && selling.value ? __("{0} spent", [amount(c.spent)]) : "",
    bar: selling.value ? share(c.spent, c.budget) ?? undefined : undefined,
    alarm: c.budget && c.spent > c.budget,
    // The figure is the whole tree's; it's changed here only where it's the
    // project's own, with no sub-projects. With cost types adding it up, the
    // dialog changes the time budget and planned hours only.
    action:
      props.said.can_budget && !props.said.overview.sub_projects?.count
        ? { icon: "lucide-pencil", label: __("Change Budget"), onClick: changeBudget }
        : null,
  };
};
const over = (c) => (c.budget && c.forecast_cost > c.budget ? __("{0} over budget", [amount(c.forecast_cost - c.budget)]) : "");
const onOrder = (c) => (c.open_orders ? __("{0} more on order", [amount(c.open_orders)]) : "");
const costFigure = (c) => ({ title: __("Cost"), value: amount(c.spent), note: onOrder(c), alarm: c.budget && c.forecast_cost > c.budget });
const soFar = (c, whole) => ({
  title: __("Margin So Far"),
  value: amount(c.margin),
  note: whole && c.margin > 0 ? __("{0}% margin", [percent(c.margin, whole)]) : "",
  alarm: c.margin < 0,
});
const forecast = computed(() => {
  const c = cash.value;
  if (!selling.value) {
    const left = c.forecast_cost === null ? null : c.budget - c.forecast_cost;
    return [
      budgetFigure(),
      { title: __("Spent"), value: amount(c.spent), note: onOrder(c), bar: share(c.spent, c.budget) ?? undefined, alarm: c.budget && c.spent > c.budget },
      { title: __("Forecast Cost"), value: maybe(c.forecast_cost), alarm: c.budget && c.forecast_cost > c.budget },
      { title: __("Left"), value: maybe(left), alarm: left !== null && left < 0 },
    ];
  }
  // Time and materials earns as the work is done; an order, if there is
  // one, is what it may come to.
  if (kind.value === "Time and Materials") {
    const ordered = c.customer.find((one) => one.doctype === "Sales Order")?.value;
    return [
      ...(ordered ? [{ title: __("Ordered"), value: amount(ordered), bar: share(c.earned, ordered) ?? undefined }] : []),
      { title: __("Earned"), value: amount(c.earned), note: __("Invoiced {0}", [amount(c.invoiced)]), bar: share(c.invoiced, c.earned) ?? undefined },
      costFigure(c),
      soFar(c, c.earned),
      ...(c.budget ? [budgetFigure()] : []),
      ...(ordered && c.forecast_margin !== null ? [{ title: __("Forecast Margin"), value: amount(c.forecast_margin), alarm: c.forecast_margin < 0 }] : []),
    ];
  }
  // A retainer is its fee, month by month.
  if (kind.value === "Retainer") {
    const months = props.said.overview.months;
    return [
      ...(months?.fee ? [{ title: __("Monthly Fee"), value: money(months.fee, months.currency) }] : []),
      { title: __("Invoiced"), value: amount(c.invoiced) },
      costFigure(c),
      soFar(c, c.invoiced),
      ...(c.budget ? [budgetFigure()] : []),
    ];
  }
  const margin = c.forecast_margin;
  return [
    { title: __("Contract"), value: amount(c.contract), note: c.invoiced ? __("Invoiced {0}", [amount(c.invoiced)]) : "", bar: share(c.invoiced, c.contract) ?? undefined },
    budgetFigure(),
    {
      title: __("Forecast Cost"),
      value: maybe(c.forecast_cost),
      note: c.forecast_cost === null ? __("No budget") : [over(c), onOrder(c)].filter(Boolean).join("\n"),
      alarm: c.budget && c.forecast_cost > c.budget,
    },
    {
      title: __("Forecast Margin"),
      value: maybe(margin),
      note: c.contract && margin > 0 ? __("{0}% of the contract", [Math.round((100 * margin) / c.contract)]) : "",
      alarm: margin !== null && margin < 0,
    },
    { title: __("Margin So Far"), value: amount(c.margin), note: __("Invoiced less spent"), alarm: c.margin < 0 },
  ];
});

// Each side as its figures in order, with a bar against what was ordered.
// A figure still at nothing isn't shown: a delivery or a receipt means
// nothing on work that's never delivered.
const ORDERS = ["Sales Order", "Purchase Order"];
const side = (figures, whole) =>
  figures
    .filter((one) => one.value)
    .map((one) => {
      const progress = whole && one.doctype && one.doctype !== "Quotation" && !ORDERS.includes(one.doctype) ? share(one.value, whole) : undefined;
      return {
        key: one.label,
        label: one.label,
        value: plain(one.value),
        progress,
        dim: progress !== undefined && progress !== null ? __("{0}% of ordered", [progress]) : "",
        route: one.route,
      };
    });
const ordered = (figures) => figures.find((one) => ORDERS.includes(one.doctype))?.value;
const customer = computed(() => side(cash.value.customer, ordered(cash.value.customer)));
const cost = computed(() => [...side(cash.value.cost, ordered(cash.value.cost)), ...side(cash.value.own, 0)]);

// The budget by cost type over the project and those under it, and Other
// for what they leave out (one_project/budget.py).
const types = computed(() => cash.value.cost_types);
const typeRows = computed(() => [
  ...types.value.lines.map((one) => ({ ...one, key: one.key || one.account })),
  ...(types.value.other ? [{ ...types.value.other, key: "other", cost_type: __("Other") }] : []),
]);
// How much of a cost type's budget is spent or on order, past 100 when over.
const used = (row) => (row.budget ? Math.round((100 * (row.committed + row.spent)) / row.budget) : row.committed + row.spent ? 100 : 0);

// A cost type opens what was booked to it; the time opens Time.
const opened = ref(null);
const showing = ref(false);
const booked = ref(null);
async function openType(row) {
  if (row.key === "time") return emit("view", "time");
  opened.value = row;
  booked.value = null;
  showing.value = true;
  const found = await call("onedesk.one_project.budget.booked", { project: props.said.name, account: row.account });
  booked.value = found.map((one) => ({
    key: `${one.doctype}/${one.name}`,
    label: __(one.doctype),
    sub: one.name,
    dim: date(one.date),
    value: amount(one.amount),
    route: one.open ? `/desk/${one.doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(one.name)}` : null,
  }));
}

// A cost type the project budgets for itself is changed; one only its
// sub-projects budget for adds the project's own.
function costType(row) {
  const shown = row ? (row.own !== null ? { ...row, budget: row.own } : { account: row.account, fresh: true }) : null;
  onedesk().project.cost_type(frm(), shown, () => emit("changed"));
}
function changeBudget() {
  onedesk().project.budget(frm(), () => emit("changed"));
}
</script>
