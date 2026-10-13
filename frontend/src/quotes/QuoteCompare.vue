<template>
  <!-- One request's quotes side by side (one_inventory/quotes.py `compare`):
       each supplier asked is a column, each line a row with every supplier's
       rate in their own money and, for a quote in another money, the
       company's under it. The cheapest live rate on a line is marked. Under
       each supplier, their total and until when it holds, with Order, or
       Add Their Quote for one still to answer. -->
  <div class="overflow-x-auto">
    <List :columns="columns" :row-height="56" divider="full" class="-mx-3 min-w-max list-gap-3 list-row-px-3">
      <ListHeader>
        <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
        <ListHeaderCell class="justify-end">{{ __("Quantity") }}</ListHeaderCell>
        <ListHeaderCell v-for="one in said.suppliers" :key="one.supplier" class="justify-end">
          <span class="truncate" :title="one.name">{{ one.name }}</span>
        </ListHeaderCell>
      </ListHeader>
      <ListRow v-for="line in said.lines" :key="line.item" @click="go(`/desk/item/${encodeURIComponent(line.item)}?view=buying`)">
        <ListCell class="min-w-0">
          <div class="min-w-0">
            <div class="truncate text-base text-ink-gray-8">{{ line.name }}</div>
            <div class="truncate text-sm text-ink-gray-5">{{ line.ordered ? __("{0} · Ordered", [line.item]) : line.item }}</div>
          </div>
        </ListCell>
        <ListCell class="justify-end tabular-nums text-ink-gray-7">{{ quantity(line.qty, line.uom) }}</ListCell>
        <ListCell v-for="one in said.suppliers" :key="one.supplier" class="justify-end">
          <div v-if="line.offers[one.supplier]" class="text-end tabular-nums" :class="one.expired ? 'text-ink-gray-4 line-through' : 'text-ink-gray-8'">
            <div class="flex items-center justify-end gap-1.5">
              <Badge v-if="line.cheapest === one.supplier" :label="__('Cheapest')" :theme="line.ordered ? 'gray' : 'green'" size="sm" />
              {{ money(line.offers[one.supplier].rate, one.currency) }}
            </div>
            <div v-if="one.currency !== said.currency" class="text-sm text-ink-gray-5">{{ money(line.offers[one.supplier].base_rate, said.currency) }}</div>
          </div>
          <span v-else class="text-ink-gray-4">–</span>
        </ListCell>
      </ListRow>
      <!-- Each supplier's quote as a whole. -->
      <ListRow class="!cursor-default">
        <ListCell class="text-ink-gray-5">{{ __("Total") }}</ListCell>
        <ListCell />
        <ListCell v-for="one in said.suppliers" :key="one.supplier" class="justify-end">
          <div class="text-end">
            <template v-if="one.quote">
              <div class="tabular-nums text-ink-gray-8" :class="{ 'text-ink-gray-4 line-through': one.expired }">{{ money(one.total, one.currency) }}</div>
              <div class="text-sm text-ink-gray-5">{{ held(one) }}</div>
            </template>
            <div v-else class="text-sm text-ink-gray-5">{{ __("Not answered yet") }}</div>
          </div>
        </ListCell>
      </ListRow>
      <ListRow class="!cursor-default">
        <ListCell />
        <ListCell />
        <ListCell v-for="one in said.suppliers" :key="one.supplier" class="justify-end">
          <Button v-if="one.quote && one.draft" size="sm" :label="__('Check Quote')" @click="go(`/desk/supplier-quotation/${encodeURIComponent(one.quote)}`)" />
          <Button v-else-if="one.quote && canOrder(one)" size="sm" :label="__('Order')" @click="onedesk().quotes.order(one.quote)" />
          <Button v-else-if="one.quote" size="sm" variant="ghost" :label="__('Open Quote')" @click="go(`/desk/supplier-quotation/${encodeURIComponent(one.quote)}`)" />
          <Button v-else-if="can.quote && !said.draft" size="sm" :label="__('Add Their Quote')" @click="onedesk().quotes.add(said.name, one.supplier)" />
        </ListCell>
      </ListRow>
    </List>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Badge, Button } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { __, date, go, money, onedesk, quantity } from "../kit";

const props = defineProps({ said: { type: Object, required: true }, can: { type: Object, required: true } });

const columns = computed(() => ["minmax(12rem,1.4fr)", "7rem", ...props.said.suppliers.map(() => "minmax(9rem,1fr)")]);

// A quote may be ordered from while it holds and a line it prices is left to order.
const canOrder = (one) =>
  props.can.order && !one.expired && ["Submitted", "Partially Ordered"].includes(one.status) && props.said.lines.some((line) => !line.ordered && line.offers[one.supplier]);

function held(one) {
  if (one.draft) return __("Draft");
  if (one.expired) return __("Expired {0}", [date(one.valid_till)]);
  if (one.status === "Ordered") return __("Ordered");
  return one.valid_till ? __("Holds until {0}", [date(one.valid_till)]) : "";
}
</script>
