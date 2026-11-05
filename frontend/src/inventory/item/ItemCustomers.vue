<template>
  <div v-if="!rows.length && !adding" class="py-3 text-base text-ink-gray-5">{{ __("Not sold in 12 months") }}</div>
  <ul v-else class="divide-y divide-outline-gray-1">
    <li v-for="one in rows" :key="one.customer" class="flex gap-3 py-2.5">
      <Avatar :label="one.customer" :image="one.image" shape="square" size="md" class="mt-0.5 shrink-0" />
      <div class="min-w-0 flex-1">
        <button type="button" class="break-words text-start rounded-2 text-base text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/customer/${encodeURIComponent(one.customer)}`)">
          {{ one.customer }}
        </button>
        <div v-for="(line, i) in one.lines" :key="i" class="break-words text-sm text-ink-gray-5">{{ line }}</div>
        <div v-if="one.row" class="mt-1 flex items-center gap-1.5 whitespace-nowrap text-sm text-ink-gray-5">
          {{ __("Customer's Code") }}
          <FieldEdit :form="form" table="customer_items" :row="one.row" field="ref_code" :label="__('Customer\'s Code')" :hold="Boolean(adding) && one.row === adding" start class="text-ink-gray-8" @saved="emit('changed')" @cancel="cancel" />
        </div>
        <div v-if="adding && one.row === adding" class="mt-2 flex gap-2">
          <Button size="sm" :label="__('Cancel')" @click="cancel" />
          <Button variant="solid" size="sm" :label="__('Save')" :loading="saving" @click="save" />
        </div>
      </div>
      <div class="flex shrink-0 items-start gap-1">
        <div class="pt-0.5 text-end">
          <div class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ one.value }}</div>
          <div v-if="one.base" class="whitespace-nowrap text-sm tabular-nums text-ink-gray-5">{{ one.base }}</div>
        </div>
        <Dropdown v-if="one.actions.length" :options="one.actions" placement="right">
          <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
        </Dropdown>
      </div>
    </li>
  </ul>
</template>

<script setup>
import { computed, ref } from "vue";
import { Avatar, Button, Dropdown } from "frappe-ui";

import { FieldEdit, __, date, go, money, onedesk, quantity } from "../../kit";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const selling = computed(() => props.said.selling);
const ours = computed(() => props.said.currency);

const adding = ref(null);
const addingFor = ref(null);
const saving = ref(false);

const rows = computed(() =>
  selling.value.customers.map((one) => {
    const row = one.row || (addingFor.value === one.customer ? adding.value : null);
    const theirs = one.currency || ours.value;
    const own = theirs !== ours.value && one.their_amount !== null;
    return {
      ...one,
      row,
      value: own ? money(one.their_amount, theirs) : one.amount ? money(one.amount, ours.value) : "",
      base: own ? money(one.amount, ours.value) : "",
      lines: [
        one.qty || one.returned
          ? [__("{0} in 12 months", [quantity(one.qty, props.said.stock_uom)]), one.returned && __("{0} returned", [quantity(one.returned)])].filter(Boolean).join(" · ")
          : "",
        one.last && __("Last sold at {0} on {1}", [money(one.rate, theirs), date(one.last)]),
      ].filter(Boolean),
      actions: actions(one, row),
    };
  })
);

function actions(one, row) {
  const out = [];
  if (selling.value.can.Quotation && !props.said.disabled)
    out.push({ label: __("New Quotation"), icon: "lucide-message-square-quote", onClick: () => onedesk().item.quote(props.said.name, one.customer) });
  if (selling.value.can["Sales Order"] && !props.said.disabled)
    out.push({ label: __("New Order"), icon: "lucide-shopping-cart", onClick: () => onedesk().item.sell(props.said.name, one.customer) });
  if (props.said.can_write && !row) out.push({ label: __("Set Customer's Code"), icon: "lucide-hash", onClick: () => add(one.customer) });
  return out;
}

function add(customer) {
  cancel();
  adding.value = props.form.addRow("customer_items", { customer_name: customer });
  addingFor.value = customer;
}

async function save() {
  saving.value = true;
  try {
    if (!(await props.form.save())) return;
    adding.value = addingFor.value = null;
    emit("changed");
  } finally {
    saving.value = false;
  }
}

function cancel() {
  if (!adding.value) return;
  adding.value = addingFor.value = null;
  props.form.discard();
}
</script>
