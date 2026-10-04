<template>
  <!-- The subcontracts: each supplier's order on the project, as a card of
       how far it's billed and what's held, with Bill Progress for the next
       bill (one_project/money.py, progress.py). -->
  <div class="pb-12 pt-4">
    <div class="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2">
      <div v-if="orders.length" class="flex flex-wrap gap-x-6 gap-y-1 text-base text-ink-gray-6">
        <span>{{ __("Ordered") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("ordered")) }}</span></span>
        <span>{{ __("Billed") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("billed")) }}</span></span>
        <span>{{ __("Left to Bill") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("left")) }}</span></span>
        <span v-if="total('retention')">{{ __("Retention Held") }} <span class="tabular-nums text-ink-gray-9">{{ amount(total("retention")) }}</span></span>
      </div>
      <Button v-if="cash.can_order" class="ms-auto" size="sm" variant="solid" icon-left="lucide-plus" :label="__('New Purchase Order')" @click="order" />
    </div>

    <div v-if="!orders.length" class="flex flex-col items-center gap-3 py-16 text-center">
      <span class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"><span class="lucide-truck size-5" /></span>
      <p class="text-base text-ink-gray-7">{{ __("No subcontracts") }}</p>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="one in orders" :key="one.order" class="flex flex-col rounded-5 border border-outline-gray-2 bg-surface-base p-4">
        <div class="flex items-start gap-2">
          <div class="min-w-0 flex-1">
            <h3 class="truncate text-base font-semibold text-ink-gray-9">{{ one.supplier }}</h3>
            <button class="truncate text-sm text-ink-gray-5 hover:underline" @click="go(one.route)">{{ one.order }}<span v-if="one.ordered_on"> · {{ date(one.ordered_on) }}</span></button>
          </div>
          <Badge v-if="STATUS[one.status]" :label="__(one.status)" :theme="STATUS[one.status]" size="md" />
        </div>

        <div class="mt-4 flex items-baseline justify-between gap-2">
          <span class="text-xl font-semibold tabular-nums text-ink-gray-9">{{ amount(one.ordered) }}</span>
          <span class="text-sm text-ink-gray-5">{{ billedShare(one) >= 100 ? __("Billed") : __("{0}% billed", [billedShare(one)]) }}</span>
        </div>
        <Progress :value="billedShare(one)" size="md" class="mt-2" />

        <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          <template v-for="fact in facts(one)" :key="fact.label">
            <dt class="text-ink-gray-5">{{ fact.label }}</dt>
            <dd class="text-end tabular-nums text-ink-gray-8">{{ fact.value }}</dd>
          </template>
        </dl>

        <div class="mt-auto flex justify-end gap-2 pt-4">
          <Button size="sm" variant="ghost" :label="__('Open Order')" @click="go(one.route)" />
          <Button v-if="cash.can_bill && one.can_bill" size="sm" :label="__('Bill Progress')" @click="bill(one)" />
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Badge, Button, Progress } from "frappe-ui";

import { __, date, go, money, newDoc, onedesk } from "../kit";

const props = defineProps({ said: { type: Object, required: true } });

const STATUS = { "On Hold": "orange", Closed: "gray", Completed: "green" };
const cash = computed(() => props.said.money);
const orders = computed(() => cash.value.suppliers);
const amount = (value) => money(value, cash.value.currency);
const total = (key) => orders.value.reduce((sum, one) => sum + (one[key] || 0), 0);
const billedShare = (one) => (one.ordered ? Math.min(100, Math.round((100 * one.billed) / one.ordered)) : 0);

function facts(one) {
  const shown = [
    { label: __("Billed"), value: amount(one.billed) },
    { label: __("Left to Bill"), value: amount(one.left) },
    { label: __("Paid"), value: amount(one.paid) },
  ];
  if (one.retention) shown.push({ label: __("Retention Held"), value: amount(one.retention) });
  if (one.advance) shown.push({ label: __("Advance"), value: amount(one.advance) });
  return shown;
}

// Bill Progress is desk's own dialog, the one on the order's form.
const bill = (one) => onedesk().progress.ask({ doctype: "Purchase Order", doc: { name: one.order } });
const order = () => newDoc("Purchase Order", { project: props.said.name });
</script>
