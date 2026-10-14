<template>
  <!-- Requests for quotation as a table, modelled on Odoo Purchase's list of
       RFQs: what is asked for, where it stands, each supplier asked and
       whether they answered, and when (one_inventory/quotes.py `asked`). -->
  <p v-if="!requests.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>
  <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Request for Quotation") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Suppliers") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Answered") }}</ListHeaderCell>
      <ListHeaderCell class="max-xl:hidden">{{ __("Asked") }}</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <ListRows :items="requests" row-key="name" v-slot="{ item }">
      <ListRow @click="emit('compare', item.name)">
        <ListCell>
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.what }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="state(item).label" :theme="state(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ [item.name, item.project].filter(Boolean).join(" · ") }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="state(item).label" :theme="state(item).theme" size="md" /></ListCell>
        <ListCell class="min-w-0 flex-wrap gap-1.5 max-lg:hidden">
          <Badge v-for="one in item.suppliers" :key="one.supplier" :label="one.name" :theme="one.answered ? 'green' : 'gray'" size="sm" :title="one.answered ? __('Answered') : __('Not answered yet')">
            <template #prefix><span :class="one.answered ? 'lucide-check' : 'lucide-clock'" class="size-3" aria-hidden="true" /></template>
          </Badge>
        </ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ __("{0} of {1}", [count(item.answered), count(item.suppliers.length)]) }}</ListCell>
        <ListCell class="max-xl:hidden">
          <div class="flex flex-col">
            <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ item.date ? date(item.date) : "–" }}</span>
            <span v-if="item.wanted" class="whitespace-nowrap text-sm text-ink-gray-5">{{ __("Required By {0}", [date(item.wanted)]) }}</span>
          </div>
        </ListCell>
        <ListCell class="justify-end" @click.stop>
          <Dropdown :options="actions(item)" placement="right">
            <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, count, date, go, onedesk } from "../kit";

const props = defineProps({ requests: { type: Array, required: true }, can: { type: Object, required: true }, empty: String });
const emit = defineEmits(["compare"]);

// Answered is the one a phone keeps; the status, the suppliers and the day join as the page widens.
const columns = {
  base: ["minmax(0,1fr)", "auto", "2rem"],
  sm: ["minmax(0,1fr)", "7rem", "6rem", "2rem"],
  lg: ["minmax(0,1fr)", "7rem", "minmax(0,1fr)", "6rem", "2rem"],
  xl: ["minmax(0,1fr)", "7rem", "minmax(0,1fr)", "6rem", "8rem", "2rem"],
};

function state(one) {
  if (one.draft) return { label: __("Draft"), theme: "gray" };
  if (one.ordered) return { label: __("Ordered"), theme: "green" };
  if (one.suppliers.some((row) => !row.answered)) return { label: __("Waiting"), theme: "amber" };
  return { label: __("Answered"), theme: "blue" };
}

const actions = (one) =>
  [
    one.answered && { label: __("Compare"), icon: "lucide-columns-3", onClick: () => emit("compare", one.name) },
    ...(props.can.quote && !one.draft
      ? one.suppliers.filter((row) => !row.answered).map((row) => ({ label: __("Add Supplier Quotation from {0}", [row.name]), icon: "lucide-plus", onClick: () => onedesk().quotes.add(one.name, row.supplier) }))
      : []),
    { label: __("Open Request for Quotation"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/request-for-quotation/${encodeURIComponent(one.name)}`) },
  ].filter(Boolean);
</script>
