<template>
  <div v-if="!rows.length && !adding" class="py-3 text-base text-ink-gray-5">{{ __("Never bought") }}</div>
  <ul v-else class="divide-y divide-outline-gray-1">
    <li v-for="one in rows" :key="one.supplier" class="flex gap-3 py-2.5">
      <Avatar :label="one.supplier" :image="one.image" shape="square" size="md" class="mt-0.5 shrink-0" />
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-2">
          <button type="button" class="truncate rounded-2 text-base text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/supplier/${encodeURIComponent(one.supplier)}`)">
            {{ one.supplier }}
          </button>
          <Badge v-if="one.default" :label="__('Default')" theme="blue" size="sm" />
        </div>
        <div v-for="(line, i) in one.lines" :key="i" class="truncate text-sm text-ink-gray-5">{{ line }}</div>
        <div v-if="one.row" class="mt-1 flex items-center gap-1.5 whitespace-nowrap text-sm text-ink-gray-5">
          {{ __("Part Number") }}
          <FieldEdit :form="form" table="supplier_items" :row="one.row" field="supplier_part_no" :label="__('Part Number')" :hold="one.row === adding" start class="text-ink-gray-8" @saved="emit('changed')" @cancel="cancel" />
        </div>
        <div v-if="adding && one.row === adding" class="mt-2 flex gap-2">
          <Button size="sm" :label="__('Cancel')" @click="cancel" />
          <Button variant="solid" size="sm" :label="__('Save')" :loading="saving" @click="save" />
        </div>
      </div>
      <div class="flex shrink-0 items-start gap-1">
        <div class="pt-0.5 text-end">
          <div class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ one.price }}</div>
          <div v-if="one.base" class="whitespace-nowrap text-sm tabular-nums text-ink-gray-5">{{ one.base }}</div>
        </div>
        <Dropdown v-if="one.actions.length" :options="one.actions" placement="right">
          <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
        </Dropdown>
      </div>
    </li>
    <li v-if="adding && !rows.some((one) => one.row === adding)" class="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5 text-sm text-ink-gray-5">
      <span class="flex items-center gap-1.5 whitespace-nowrap">{{ __("Supplier") }}<FieldEdit :form="form" table="supplier_items" :row="adding" field="supplier" :label="__('Supplier')" hold start class="text-ink-gray-8" @cancel="cancel" /></span>
      <span class="flex items-center gap-1.5 whitespace-nowrap">{{ __("Part Number") }}<FieldEdit :form="form" table="supplier_items" :row="adding" field="supplier_part_no" :label="__('Part Number')" hold start class="text-ink-gray-8" @cancel="cancel" /></span>
      <div class="flex basis-full gap-2">
        <Button size="sm" :label="__('Cancel')" @click="cancel" />
        <Button variant="solid" size="sm" :label="__('Save')" :loading="saving" @click="save" />
      </div>
    </li>
  </ul>
</template>

<script setup>
import { computed, ref } from "vue";
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";

import { FieldEdit, __, date, go, money, onedesk, quantity } from "../../kit";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const buying = computed(() => props.said.buying);
const ours = computed(() => props.said.currency);

const adding = ref(null);
const addingFor = ref(null);
const saving = ref(false);

const rows = computed(() =>
  buying.value.suppliers.map((one) => {
    const row = one.row || (addingFor.value === one.supplier ? adding.value : null);
    const theirs = one.currency || ours.value;
    return {
      ...one,
      row,
      price: one.rate !== null ? money(one.rate, theirs) : "",
      base: one.rate !== null && theirs !== ours.value ? money(one.base_rate, ours.value) : "",
      lines: [
        one.last &&
          (one.before !== null
            ? __("Last ordered {0}, before that {1}", [date(one.last), money(one.before, theirs)])
            : __("Last ordered {0}", [date(one.last)])),
        one.agreed && __("Agreed at {0}, {1} left until {2}", [money(one.agreed.rate, theirs), quantity(one.agreed.left, props.said.stock_uom), date(one.agreed.until)]),
      ].filter(Boolean),
      actions: actions(one, row),
    };
  })
);

function actions(one, row) {
  const out = [];
  if (props.said.can["Purchase Order"] && !props.said.disabled)
    out.push({ label: __("Order from Them"), icon: "lucide-shopping-cart", onClick: () => onedesk().item.order(props.said.name, one.supplier) });
  if (buying.value.can["Request for Quotation"] && !props.said.disabled)
    out.push({ label: __("Request for Quotation"), icon: "lucide-message-square-quote", onClick: () => onedesk().item.ask(props.said.name, one.supplier) });
  if (props.said.can_write && !one.default) out.push({ label: __("Make Default"), icon: "lucide-star", onClick: () => makeDefault(one.supplier) });
  if (props.said.can_write && !row) out.push({ label: __("Set Part Number"), icon: "lucide-hash", onClick: () => add(one.supplier) });
  return out;
}

function add(supplier = null) {
  cancel();
  adding.value = props.form.addRow("supplier_items", supplier ? { supplier } : {});
  addingFor.value = supplier;
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

async function makeDefault(supplier) {
  cancel();
  const kept = buying.value.default_row;
  if (kept) await props.form.row("item_defaults", kept).set("default_supplier", supplier);
  else props.form.addRow("item_defaults", { company: buying.value.company, default_supplier: supplier });
  if (await props.form.save()) emit("changed");
}

defineExpose({ add });
</script>
