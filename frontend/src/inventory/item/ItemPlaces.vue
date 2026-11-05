<template>
  <div v-if="!rows.length" class="py-3 text-base text-ink-gray-5">{{ __("Not kept anywhere yet") }}</div>
  <ul v-else class="divide-y divide-outline-gray-1">
    <li v-for="one in rows" :key="one.warehouse" class="flex gap-3 py-2.5">
      <span class="mt-2 h-2 w-2 shrink-0 rounded-full" :class="one.low ? 'bg-surface-amber-5' : 'bg-surface-gray-4'" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-2">
          <button type="button" class="break-words text-start rounded-2 text-base text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/warehouse/${encodeURIComponent(one.warehouse)}`)">
            {{ one.called }}
          </button>
          <Badge v-if="one.low" :label="__('Low')" theme="amber" size="sm" />
        </div>
        <div class="break-words text-sm tabular-nums text-ink-gray-5">{{ one.said }}</div>
        <Progress v-if="one.bar !== null" :value="one.bar" size="sm" class="mt-1.5 max-w-64" />
        <div v-if="one.row" class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-gray-5">
          <span class="flex items-center gap-1.5 whitespace-nowrap">{{ __("Reorders At") }}<FieldEdit :form="form" table="reorder_levels" :row="one.row" field="warehouse_reorder_level" :label="__('Reorders At')" :hold="Boolean(adding) && one.row === adding" start class="text-ink-gray-8" @saved="emit('changed')" @cancel="cancel" /></span>
          <span class="flex items-center gap-1.5 whitespace-nowrap">{{ __("Orders") }}<FieldEdit :form="form" table="reorder_levels" :row="one.row" field="warehouse_reorder_qty" :label="__('Orders')" :hold="Boolean(adding) && one.row === adding" start class="text-ink-gray-8" @saved="emit('changed')" @cancel="cancel" /></span>
        </div>
        <div v-if="adding && one.row === adding" class="mt-2 flex gap-2">
          <Button size="sm" :label="__('Cancel')" @click="cancel" />
          <Button variant="solid" size="sm" :label="__('Save')" :loading="saving" @click="save" />
        </div>
      </div>
      <div class="flex shrink-0 items-start gap-1">
        <span class="whitespace-nowrap pt-0.5 text-base tabular-nums text-ink-gray-7">{{ quantity(one.on_hand, uom) }}</span>
        <Dropdown v-if="one.actions.length" :options="one.actions" placement="right">
          <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
        </Dropdown>
      </div>
    </li>
  </ul>
</template>

<script setup>
import { computed, ref } from "vue";
import { Badge, Button, Dropdown, Progress } from "frappe-ui";

import { FieldEdit, __, can, go, money, onedesk, quantity } from "../../kit";

const props = defineProps({ said: { type: Object, required: true }, form: { type: Object, required: true } });
const emit = defineEmits(["changed"]);
const uom = computed(() => props.said.stock_uom);

const adding = ref(null);
const addingTo = ref(null);
const saving = ref(false);

const rows = computed(() =>
  props.said.stock.places.map((one) => {
    const full = one.level + one.order_qty;
    const row = one.row || (addingTo.value === one.warehouse ? adding.value : null);
    return {
      ...one,
      row,
      said: [
        one.reserved && __("{0} promised", [quantity(one.reserved)]),
        __("{0} free to use", [quantity(one.free)]),
        one.ordered && __("{0} on order", [quantity(one.ordered)]),
        money(one.value, props.said.currency),
      ]
        .filter(Boolean)
        .join(" · "),
      bar: one.level && full ? Math.min(100, Math.max(0, Math.round((one.on_hand / full) * 100))) : null,
      actions: actions(one, row),
    };
  })
);

function actions(one, row) {
  const out = [];
  if (props.said.is_stock_item && can("create", "Stock Entry"))
    out.push({ label: __("Transfer Stock"), icon: "lucide-arrow-left-right", onClick: () => onedesk().item.move(props.said.name, one.warehouse) });
  if (props.said.is_stock_item && can("create", "Stock Reconciliation"))
    out.push({ label: __("Count Stock"), icon: "lucide-list-checks", onClick: () => onedesk().item.count(props.said.name, false, one.warehouse) });
  if (!row && props.said.can_write) out.push({ label: __("Set Reorder Level"), icon: "lucide-bell-ring", onClick: () => add(one.warehouse) });
  return out;
}

function add(warehouse) {
  cancel();
  adding.value = props.form.addRow("reorder_levels", { warehouse, material_request_type: "Purchase" });
  addingTo.value = warehouse;
}

async function save() {
  saving.value = true;
  try {
    if (!(await props.form.save())) return;
    adding.value = addingTo.value = null;
    emit("changed");
  } finally {
    saving.value = false;
  }
}

function cancel() {
  if (!adding.value) return;
  adding.value = addingTo.value = null;
  props.form.discard();
}
</script>
