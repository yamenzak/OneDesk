<template>
  <!-- Where the project's money stands and where it's heading: the forecast,
       the customer's side and the cost side, and the budget by cost type.
       Every figure opens the documents behind it (one_project/money.py). -->
  <div class="pb-12 pt-2">
    <Section :title="__('Forecast')">
      <Figures :figures="forecast" />
    </Section>

    <div class="grid gap-x-10 border-b border-outline-gray-1 lg:grid-cols-2 [&>section]:border-0">
      <Section v-if="selling" :title="__('Customer')">
        <Rows :rows="customer" :empty="__('No sales yet')" />
      </Section>
      <Section :title="__('Cost')">
        <Rows :rows="cost" :empty="__('No costs yet')" />
      </Section>
    </div>

    <section class="py-5">
      <div class="mb-3 flex items-center justify-between gap-2">
        <h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Cost Types") }}</h2>
        <Button v-if="types?.can_set" size="sm" icon-left="lucide-plus" :label="__('Add Cost Type')" @click="costType()" />
      </div>
      <Loading v-if="!types" />
      <div v-else-if="!types.lines.length" class="py-3 text-base text-ink-gray-5">{{ __("No cost types") }}</div>
      <List v-else :columns="['minmax(0,1.4fr)', '7rem', '7rem', '7rem', '7rem', 'minmax(6rem,1fr)']" :row-height="44" divider="full" class="-mx-3 list-gap-3 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Cost Type") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Budget") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Committed") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Spent") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Left") }}</ListHeaderCell>
          <ListHeaderCell>{{ __("Used") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="types.lines" row-key="account" v-slot="{ item }">
          <ListRow v-bind="types.can_set ? { onClick: () => costType(item) } : {}">
            <ListCell class="min-w-0"><span class="truncate text-base text-ink-gray-8">{{ item.cost_type }}</span></ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ amount(item.budget) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ amount(item.committed) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ amount(item.spent) }}</ListCell>
            <ListCell class="justify-end tabular-nums" :class="item.left < 0 ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ amount(item.left) }}</ListCell>
            <ListCell><Progress :value="used(item)" size="md" class="w-full" /></ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Figures, Loading, Rows, Section, __, call, money, onedesk } from "../kit";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const cash = computed(() => props.said.money);
const amount = (value) => money(value, cash.value.currency);
const share = (part, whole) => (whole ? Math.max(0, Math.min(100, Math.round((100 * part) / whole))) : null);
const frm = () => ({ doctype: "Project", doc: { name: props.said.name } });

// The forecast: what the contract brings in, what the work will cost by the
// budget and the orders, and the margin either way. A project with no
// customer and nothing ordered by one has no contract: its forecast is the
// budget and what's left of it.
const selling = computed(() => Boolean(props.said.customer || cash.value.contract));
const budgetFigure = () => {
  const c = cash.value;
  return {
    title: __("Budget"),
    value: c.budget ? amount(c.budget) : "–",
    note: c.budget && selling.value ? __("{0} spent", [amount(c.spent)]) : "",
    bar: selling.value ? share(c.spent, c.budget) ?? undefined : undefined,
    alarm: c.budget && c.spent > c.budget,
    // The figure is the whole tree's; it's changed here only where it's the
    // project's own, with no cost types adding it up and no sub-projects.
    action:
      props.said.can_budget && types.value && !types.value.lines.length && !props.said.overview.sub_projects?.length
        ? { icon: "lucide-pencil", label: __("Change Budget"), onClick: changeBudget }
        : null,
  };
};
const onOrder = (c) => (c.open_orders ? __("{0} more on order", [amount(c.open_orders)]) : "");
const forecast = computed(() => {
  const c = cash.value;
  if (!selling.value) {
    const left = c.budget - c.forecast_cost;
    return [
      budgetFigure(),
      { title: __("Spent"), value: amount(c.spent), note: onOrder(c), bar: share(c.spent, c.budget) ?? undefined, alarm: c.budget && c.spent > c.budget },
      { title: __("Forecast Cost"), value: amount(c.forecast_cost), alarm: c.budget && c.forecast_cost > c.budget },
      { title: __("Left"), value: c.budget ? amount(left) : "–", alarm: c.budget && left < 0 },
    ];
  }
  const margin = c.forecast_margin;
  return [
    { title: __("Contract"), value: amount(c.contract), note: c.invoiced ? __("Invoiced {0}", [amount(c.invoiced)]) : "", bar: share(c.invoiced, c.contract) ?? undefined },
    budgetFigure(),
    { title: __("Forecast Cost"), value: amount(c.forecast_cost), note: onOrder(c), alarm: c.budget && c.forecast_cost > c.budget },
    { title: __("Forecast Margin"), value: amount(margin), note: c.contract && margin >= 0 ? __("{0}% of the contract", [Math.round((100 * margin) / c.contract)]) : "", alarm: margin < 0 },
    { title: __("Margin So Far"), value: amount(c.margin), note: __("Invoiced less spent"), alarm: c.margin < 0 },
  ];
});

// Each side as its figures in order, with a bar against what was ordered.
const ORDERS = ["Sales Order", "Purchase Order"];
const side = (figures, whole) =>
  figures.map((one) => ({
    key: one.label,
    label: one.label,
    value: amount(one.value),
    progress: whole && one.doctype && one.doctype !== "Quotation" && !ORDERS.includes(one.doctype) ? share(one.value, whole) : undefined,
    route: one.route,
  }));
const ordered = (figures) => figures.find((one) => ORDERS.includes(one.doctype))?.value;
// A side where nothing has happened yet says so, not a column of zeros.
const any = (figures) => figures.some((one) => one.value);
const customer = computed(() => (any(cash.value.customer) ? side(cash.value.customer, ordered(cash.value.customer)) : []));
const cost = computed(() =>
  any([...cash.value.cost, ...cash.value.own]) ? [...side(cash.value.cost, ordered(cash.value.cost)), ...side(cash.value.own.filter((one) => one.value), 0)] : []
);

// The budget by cost type: ERPNext's Budget against the project, one per
// expense account (one_project/budget.py).
const types = ref(null);
async function loadTypes() {
  types.value = await call("onedesk.one_project.budget.lines", { project: props.said.name });
}
watch(() => [props.said.name, props.said.modified, cash.value.spent, cash.value.open_orders], loadTypes, { immediate: true });
const used = (row) => share(row.committed + row.spent, row.budget) ?? 0;

function costType(row) {
  onedesk().project.cost_type(frm(), row || null, (said) => {
    types.value = said;
    emit("changed");
  });
}
function changeBudget() {
  onedesk().project.budget(frm(), () => emit("changed"));
}
</script>
