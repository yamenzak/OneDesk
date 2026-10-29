<template>
  <p v-if="!orders.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Makes") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Supplier") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end max-xl:hidden">{{ __("Supplied") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Received") }}</ListHeaderCell>
      <ListHeaderCell class="max-md:hidden">{{ done ? __("Sent On") : __("Due") }}</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <ListRows :items="orders" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/subcontracting-order/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="made(item).name" :image="made(item).image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ title(item) }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="state(item).label" :theme="state(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ [item.name, item.project_name].filter(Boolean).join(" · ") }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="min-w-0 gap-2 max-lg:hidden">
          <Avatar :label="item.supplier_name || item.supplier" size="sm" />
          <span class="truncate text-base text-ink-gray-7">{{ item.supplier_name || item.supplier }}</span>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="state(item).label" :theme="state(item).theme" size="md" /></ListCell>
        <ListCell class="justify-end max-xl:hidden">
          <div v-if="item.materials.length" class="flex min-w-0 flex-col items-end">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">
              <template v-if="item.materials.length === 1">{{ quantity(item.materials[0].sent) }} <span class="text-sm text-ink-gray-5">{{ __(item.materials[0].unit) }}</span></template>
              <template v-else>{{ __("{0} of {1}", [count(sentAll(item)), count(item.materials.length)]) }}</template>
            </span>
            <span class="max-w-full truncate text-sm text-ink-gray-5">{{ item.materials.length === 1 ? item.materials[0].name : __("supplied") }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell class="justify-end">
          <div class="flex w-full flex-col items-end gap-1.5">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ __("{0} of {1}", [quantity(back(item)), quantity(asked(item))]) }} <span class="text-sm text-ink-gray-5">{{ __(made(item).unit || "") }}</span></span>
            <Progress :value="asked(item) ? Math.min(100, Math.round((100 * back(item)) / asked(item))) : 0" size="sm" class="w-full max-w-24" />
          </div>
        </ListCell>
        <ListCell class="max-md:hidden">
          <div v-if="done ? item.transaction_date : item.schedule_date" class="flex flex-col">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ date(done ? item.transaction_date : item.schedule_date) }}</span>
            <span v-if="!done" class="whitespace-nowrap text-sm" :class="item.late ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ fromToday(item.schedule_date) }}</span>
          </div>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell class="justify-end" @click.stop>
          <Dropdown v-if="actions(item).length" :options="actions(item)" placement="right">
            <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Avatar, Badge, Button, Dropdown, Progress } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, count, date, fromToday, go, onedesk, quantity } from "../../kit";

const props = defineProps({
  orders: { type: Array, required: true },
  can: { type: Object, required: true },
  done: Boolean,
  empty: String,
});

const columns = {
  base: ["minmax(0,1fr)", "7rem", "2rem"],
  sm: ["minmax(0,1fr)", "8rem", "8rem", "2rem"],
  md: ["minmax(0,1fr)", "8rem", "8rem", "7rem", "2rem"],
  lg: ["minmax(0,1fr)", "minmax(0,12rem)", "8rem", "8rem", "7rem", "2rem"],
  xl: ["minmax(0,1fr)", "minmax(0,12rem)", "8rem", "9rem", "8rem", "7rem", "2rem"],
};

const STATES = {
  Open: [() => __("Open"), "amber"],
  "Partial Material Transferred": [() => __("Partial Material Transferred"), "amber"],
  "Material Transferred": [() => __("Material Transferred"), "blue"],
  "Partially Received": [() => __("Partially Received"), "blue"],
  Completed: [() => __("Completed"), "green"],
  Closed: [() => __("Closed"), "gray"],
};
function state(one) {
  const [label, theme] = STATES[one.status] || [() => __(one.status), "gray"];
  return { label: label(), theme };
}

const made = (one) => one.makes[0] || { name: one.name };
const title = (one) => (one.makes.length > 1 ? __("{0} and {1} more", [made(one).name, one.makes.length - 1]) : made(one).name);
const back = (one) => one.makes.reduce((sum, row) => sum + row.back, 0);
const asked = (one) => one.makes.reduce((sum, row) => sum + row.qty, 0);
const sentAll = (one) => one.materials.filter((row) => row.sent >= row.needed).length;

const actions = (one) =>
  [
    props.can.send && ["Open", "Partial Material Transferred"].includes(one.status) && { label: __("Transfer Material"), icon: "lucide-truck", onClick: () => onedesk().sent_out.send(one.name) },
    props.can.receive && ["Partial Material Transferred", "Material Transferred", "Partially Received"].includes(one.status) && { label: __("Subcontracting Receipt"), icon: "lucide-package-check", onClick: () => onedesk().sent_out.receive(one.name) },
    one.purchase_order && { label: __("Open Purchase Order"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/purchase-order/${encodeURIComponent(one.purchase_order)}`) },
  ].filter(Boolean);
</script>
