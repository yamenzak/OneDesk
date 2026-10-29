<template>
  <li class="flex gap-3 py-2.5">
    <div class="min-w-0 flex-1">
      <button type="button" class="truncate rounded-2 text-base text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/item-price/${encodeURIComponent(price.name)}`)">
        {{ price.price_list }}<span v-if="price.supplier || price.customer" class="text-ink-gray-5"> · {{ price.supplier || price.customer }}</span>
      </button>
      <div v-if="lines.length" class="truncate text-sm text-ink-gray-5">{{ lines.join(" · ") }}</div>
      <div v-if="below" class="truncate text-sm text-ink-gray-5">{{ __("Sold at {0} to {1} on {2}", [money(below.rate, below.currency), below.customer, date(below.on)]) }}</div>
      <div v-if="differs" class="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-gray-5">
        {{ __("Last paid {0} on {1}", [money(last.rate, last.currency), date(last.on)]) }}
        <Button v-if="writable" size="sm" :label="__('Use Last Price')" :loading="using" @click="useLast" />
      </div>
    </div>
    <div class="flex shrink-0 items-center gap-1.5 text-base tabular-nums text-ink-gray-7">
      <FieldEdit :form="form" field="price_list_rate" :label="__('Price')" @saved="emit('changed')" />
      <span class="whitespace-nowrap text-ink-gray-5">/ {{ __(price.uom || uom) }}</span>
    </div>
  </li>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";

import { FieldEdit, __, date, go, money, useForm } from "../../kit";

const props = defineProps({
  price: { type: Object, required: true },
  last: Object,
  uom: String,
  sales: Array,
});
const emit = defineEmits(["changed"]);

const form = useForm("Item Price", computed(() => props.price.name));
const using = ref(false);

const writable = computed(() => form.status("price_list_rate") === "Write");
const lines = computed(() => [props.price.valid_upto && __("Until {0}", [date(props.price.valid_upto)])].filter(Boolean));
const differs = computed(() => {
  const last = props.last;
  if (!last || last.currency !== props.price.currency) return false;
  if ((last.uom || props.uom) !== (props.price.uom || props.uom)) return false;
  return Number(last.rate) !== Number(form.value("price_list_rate") ?? props.price.price_list_rate);
});

const below = computed(() => {
  const price = Number(form.value("price_list_rate") ?? props.price.price_list_rate);
  const unit = props.price.uom || props.uom;
  return (props.sales || []).find((one) => one.currency === props.price.currency && (one.uom || props.uom) === unit && Number(one.rate) < price) || null;
});

async function useLast() {
  using.value = true;
  try {
    await form.set("price_list_rate", props.last.rate);
    if (await form.save()) emit("changed");
  } finally {
    using.value = false;
  }
}
</script>
