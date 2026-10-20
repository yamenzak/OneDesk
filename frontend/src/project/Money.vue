<template>
  <div class="pb-12">
    <div class="flex flex-wrap items-center gap-2 pb-2">
      <h2 class="me-auto flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
        <span class="lucide-wallet size-4 text-ink-gray-5" aria-hidden="true" />{{ __("Money") }}
      </h2>
      <Button v-if="can('create', 'Stock Entry')" size="sm" icon-left="lucide-package-minus" :label="__('Issue Stock')" @click="issueStock" />
      <Button v-if="can('create', 'Stock Entry')" size="sm" icon-left="lucide-package-plus" :label="__('Return to Store')" @click="returnStock" />
      <Button v-if="can('create', 'Expense Claim')" size="sm" icon-left="lucide-plus" :label="__('New Expense Claim')" @click="newDocIn('Expense Claim', { project: said.name, company: said.company }, parts)" />
    </div>
    <PlaceSpot :said="spot" class="mb-3" />
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
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ amount(item.budget) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ amount(item.committed) }}</ListCell>
            <ListCell class="justify-end tabular-nums text-ink-gray-7 max-md:hidden">{{ amount(item.spent) }}</ListCell>
            <ListCell class="justify-end tabular-nums" :class="item.left < 0 ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ amount(item.left) }}</ListCell>
            <ListCell class="gap-2">
              <Progress :value="Math.min(100, used(item))" size="md" class="w-full" />
              <span class="w-10 shrink-0 text-end text-sm tabular-nums" :class="used(item) > 100 ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ used(item) }}%</span>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </section>

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

import { Figures, Loading, PlaceSpot, Rows, Section, __, call, can, date, money, newDocIn, onedesk, requires } from "../kit";
import { useParts } from "./only";
import { usePlace } from "./place";

const props = defineProps({ said: { type: Object, required: true } });
const emit = defineEmits(["changed", "view"]);
const parts = useParts();

const cash = computed(() => props.said.money);
const amount = (value) => money(value, cash.value.currency);
const withTax = (gross, net) => (gross !== undefined && gross !== null && Math.abs(gross - net) >= 0.005 ? { label: __("With tax"), value: amount(gross) } : undefined);
const maybe = (value) => (value === null || value === undefined ? "–" : amount(value));
const share = (part, whole) => (whole ? Math.max(0, Math.min(100, Math.round((100 * part) / whole))) : null);
const percent = (part, whole) => (whole ? Math.round((100 * part) / whole) : null);
const frm = () => ({ doctype: "Project", doc: { name: props.said.name } });
const issueStock = () =>
  requires(["/assets/onedesk/js/item_actions.js"]).then(() => onedesk().stock.issue({ project: props.said.name, title: props.said.title, done: () => emit("changed") }));
const returnStock = () =>
  requires(["/assets/onedesk/js/item_actions.js"]).then(() => onedesk().stock.give_back({ project: props.said.name, title: props.said.title, done: () => emit("changed") }));

const selling = computed(() => Boolean(props.said.customer || cash.value.contract));
const kind = computed(() => cash.value.kind);
const soFarOnly = computed(() => selling.value && ["Time and Materials", "Retainer"].includes(kind.value));
const budgetFigure = () => {
  const c = cash.value;
  return {
    title: __("Estimated Cost"),
    value: c.budget ? amount(c.budget) : "–",
    note: c.budget && selling.value ? __("{0} spent", [amount(c.spent)]) : "",
    bar: selling.value ? share(c.spent, c.budget) ?? undefined : undefined,
    alarm: c.budget && c.spent > c.budget,
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
const spot = usePlace("oneproject.money", () => ({
  project: { name: props.said.name, title: props.said.title, kind: kind.value, currency: cash.value.currency },
  money: {
    contract: cash.value.contract ?? null,
    invoiced: cash.value.invoiced ?? null,
    spent: cash.value.spent ?? null,
    budget: cash.value.budget ?? null,
    forecast_cost: cash.value.forecast_cost ?? null,
    forecast_margin: cash.value.forecast_margin ?? null,
    cost_types: (cash.value.cost_types?.lines || []).map((one) => ({ cost_type: one.cost_type, budget: one.budget, committed: one.committed, spent: one.spent, left: one.left })),
  },
}));
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
  if (kind.value === "Retainer") {
    const months = props.said.overview.months;
    return [
      ...(months?.fee ? [{ title: __("Monthly Fee"), value: money(months.fee, months.currency) }] : []),
      { title: __("Invoiced"), value: amount(c.invoiced), other: withTax(c.invoiced_with_tax, c.invoiced) },
      costFigure(c),
      soFar(c, c.invoiced),
      ...(c.budget ? [budgetFigure()] : []),
    ];
  }
  const margin = c.forecast_margin;
  return [
    { title: __("Contract"), value: amount(c.contract), other: withTax(c.contract_with_tax, c.contract), note: c.invoiced ? __("Invoiced {0}", [amount(c.invoiced)]) : "", bar: share(c.invoiced, c.contract) ?? undefined },
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

const ORDERS = ["Sales Order", "Purchase Order"];
const side = (figures, whole) =>
  figures
    .filter((one) => one.value)
    .map((one) => {
      const progress = whole && one.doctype && one.doctype !== "Quotation" && !ORDERS.includes(one.doctype) ? share(one.value, whole) : undefined;
      return {
        key: one.label,
        label: one.label,
        value: amount(one.value),
        progress,
        dim: progress !== undefined && progress !== null ? __("{0}% of ordered", [progress]) : "",
        route: one.route,
      };
    });
const ordered = (figures) => figures.find((one) => ORDERS.includes(one.doctype))?.value;
const customer = computed(() => side(cash.value.customer, ordered(cash.value.customer)));
const cost = computed(() => [...side(cash.value.cost, ordered(cash.value.cost)), ...side(cash.value.own, 0)]);

const types = computed(() => cash.value.cost_types);
const typeRows = computed(() => [
  ...types.value.lines.map((one) => ({ ...one, key: one.key || one.account })),
  ...(types.value.other ? [{ ...types.value.other, key: "other", cost_type: __("Other") }] : []),
]);
const used = (row) => (row.budget ? Math.round((100 * (row.committed + row.spent)) / row.budget) : row.committed + row.spent ? 100 : 0);

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

function costType(row) {
  const shown = row ? (row.own !== null ? { ...row, budget: row.own } : { account: row.account, fresh: true }) : null;
  onedesk().project.cost_type(frm(), shown, () => emit("changed"));
}
function changeBudget() {
  onedesk().project.budget(frm(), () => emit("changed"));
}
</script>
