<template>
  <div class="text-ink-gray-8">
    <Loading v-if="!said" />
    <component :is="PARTS[part]" v-else-if="PARTS[part] && said[KEY[part]]" :said="said" :form="form" :facts="false" @changed="load" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { Loading, call, follow, followList, useForm } from "../../kit";
import ItemBuying from "./ItemBuying.vue";
import ItemMaking from "./ItemMaking.vue";
import ItemSelling from "./ItemSelling.vue";
import ItemStock from "./ItemStock.vue";

const PARTS = { stock: ItemStock, buying: ItemBuying, selling: ItemSelling, making: ItemMaking };
const KEY = { stock: "stock", buying: "buying", selling: "selling", making: "making" };

const props = defineProps({ item: { type: String, required: true }, part: { type: String, required: true }, frm: { type: Object, default: null } });

const said = ref(null);
const form = useForm("Item", computed(() => props.item), props.frm);

async function load() {
  const asked = props.item;
  const shared = props.frm ? (props.frm.one_item_said ||= {}) : {};
  if (shared.name !== asked || Date.now() - shared.at > 1500) {
    shared.name = asked;
    shared.at = Date.now();
    shared.got = call("onedesk.one_inventory.view.read", { item: asked });
  }
  const got = await shared.got;
  if (asked === props.item) said.value = got;
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 600);
};
let stop = [];
watch(
  () => [props.item, props.part],
  () => {
    stop.forEach((one) => one());
    said.value = null;
    stop = [follow("Item", props.item, load), ...[
  "Bin", "Stock Ledger Entry", "Stock Entry", "Serial No", "Batch", "Purchase Order", "Supplier Quotation", "Blanket Order",
  "Item Manufacturer", "Quotation", "Sales Order", "Sales Invoice", "Work Order", "Work Order Operation", "Material Request",
  "Item Price", "BOM", "BOM Item", "BOM Operation", "Asset", "Employee", "File", "Item Attribute Value",
].map((one) => followList(one, soon))];
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
</script>
