<template>
  <div class="text-ink-gray-8">
    <Loading v-if="!said" />
    <template v-else>
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <TextInput v-if="said.count > 8" v-model="search" class="w-full max-w-xs" type="search" :placeholder="__('Search Items')" :aria-label="__('Search Items')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <span v-else class="text-sm text-ink-gray-5">{{ summary }}</span>
        <Button v-if="said.can.order" class="ms-auto" icon-left="lucide-plus" :label="__('New Purchase Order')" @click="newDoc('Purchase Order', { supplier })" />
      </div>
      <p v-if="!rows.length" class="py-6 text-base text-ink-gray-5">{{ search ? __("No items match") : __("Nothing bought from them yet") }}</p>
      <List v-else :columns="columns" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
        <ListHeader>
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Last Price") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end max-sm:hidden">{{ __("Bought in a Year") }}</ListHeaderCell>
          <ListHeaderCell v-if="has.on_order" class="justify-end max-lg:hidden">{{ __("On Order") }}</ListHeaderCell>
          <ListHeaderCell v-if="has.lead_days" class="justify-end max-xl:hidden">{{ __("Lead Time") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" row-key="item" v-slot="{ item }">
          <ListRow @click="go(`/desk/item/${encodeURIComponent(item.item)}?view=buying`)">
            <ListCell class="min-w-0 gap-3">
              <Avatar :label="item.item_name" :image="item.image" shape="square" size="lg" />
              <div class="flex min-w-0 flex-col gap-1">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="truncate text-base font-medium" :class="item.disabled ? 'text-ink-gray-5' : 'text-ink-gray-8'">{{ item.item_name }}</span>
                  <Badge v-if="item.default" :label="__('Default')" theme="blue" size="sm" />
                  <Badge v-if="item.quoted" :label="__('Quoted')" theme="gray" size="sm" />
                </div>
                <span class="truncate text-sm text-ink-gray-5">{{ [item.item !== item.item_name && item.item, item.part_no && __("Supplier Part No {0}", [item.part_no])].filter(Boolean).join(" · ") }}</span>
              </div>
            </ListCell>
            <ListCell class="justify-end">
              <div v-if="price(item)" class="flex flex-col items-end">
                <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-8">{{ __("{0} a {1}", [money(price(item).rate, price(item).currency), __(price(item).uom)]) }}</span>
                <span class="whitespace-nowrap text-sm" :class="item.quoted?.expired ? 'text-ink-gray-4' : 'text-ink-gray-5'">{{ when(item) }}</span>
              </div>
              <span v-else class="text-base text-ink-gray-4">–</span>
            </ListCell>
            <ListCell class="justify-end max-sm:hidden">
              <div v-if="item.bought" class="flex flex-col items-end">
                <span class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ quantity(item.bought) }} <span class="text-sm text-ink-gray-5">{{ __(item.unit) }}</span></span>
                <span class="whitespace-nowrap text-sm text-ink-gray-5">{{ item.orders === 1 ? __("1 order") : __("{0} orders", [count(item.orders)]) }}</span>
              </div>
              <span v-else class="text-base text-ink-gray-4">–</span>
            </ListCell>
            <ListCell v-if="has.on_order" class="justify-end whitespace-nowrap tabular-nums max-lg:hidden">
              <template v-if="item.on_order">
                <span class="text-base text-ink-gray-8">{{ quantity(item.on_order) }}</span>
                <span class="ms-1 text-sm text-ink-gray-5">{{ __(item.unit) }}</span>
              </template>
              <span v-else class="text-base text-ink-gray-4">–</span>
            </ListCell>
            <ListCell v-if="has.lead_days" class="justify-end whitespace-nowrap text-base tabular-nums max-xl:hidden" :class="item.lead_days ? 'text-ink-gray-7' : 'text-ink-gray-4'">
              {{ item.lead_days ? (item.lead_days === 1 ? __("1 day") : __("{0} days", [item.lead_days])) : "–" }}
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
      <p v-if="said.count > said.items.length" class="mt-3 text-sm text-ink-gray-5">{{ __("Showing {0} of {1}.", [count(said.items.length), count(said.count)]) }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Badge, Button, TextInput } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { Loading, __, call, count, date, followList, go, money, newDoc, quantity } from "../../kit";

const props = defineProps({ supplier: { type: String, required: true }, onCount: Function });

const said = ref(null);
const search = ref("");
const has = computed(() => ({
  on_order: (said.value?.items || []).some((one) => one.on_order),
  lead_days: (said.value?.items || []).some((one) => one.lead_days),
}));
const columns = computed(() => {
  const order = has.value.on_order ? ["7rem"] : [];
  const lead = has.value.lead_days ? ["6rem"] : [];
  return {
    base: ["minmax(0,1fr)", "auto"],
    sm: ["minmax(0,1fr)", "11rem", "8rem"],
    lg: ["minmax(0,1fr)", "11rem", "8rem", ...order],
    xl: ["minmax(0,1fr)", "11rem", "8rem", ...order, ...lead],
  };
});

let loads = 0;
async function load() {
  const mine = ++loads;
  const got = await call("onedesk.one_inventory.supplier_items.read", { supplier: props.supplier });
  if (mine !== loads) return;
  said.value = got;
  props.onCount?.(got.count);
}
watch(() => props.supplier, load, { immediate: true });

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
const stop = ["Purchase Order", "Supplier Quotation", "Blanket Order", "Item", "UOM"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});

const rows = computed(() => {
  const words = search.value.trim().toLowerCase();
  return (said.value?.items || []).filter((one) => !words || [one.item, one.item_name, one.part_no].some((text) => text?.toLowerCase().includes(words)));
});
const summary = computed(() => {
  const s = said.value;
  return [s.count === 1 ? __("1 item") : __("{0} items", [count(s.count)]), s.on_order && __("{0} on order", [count(s.on_order)])].filter(Boolean).join(" · ");
});

const price = (one) => (one.agreed ? { ...one.last, rate: one.agreed.rate, currency: one.last?.currency || said.value.currency, uom: one.last?.uom || one.unit } : one.last || one.quoted);
function when(one) {
  if (one.agreed) return __("Agreed until {0}", [date(one.agreed.until)]);
  if (one.last) return [date(one.last.on), one.before && __("was {0}", [money(one.before, one.last.currency)])].filter(Boolean).join(" · ");
  if (one.quoted.expired) return __("Quoted {0}, expired", [date(one.quoted.on)]);
  return one.quoted.until ? __("Quoted, valid till {0}", [date(one.quoted.until)]) : __("Quoted {0}", [date(one.quoted.on)]);
}
</script>
