<template>
  <Page wide>
    <Loading v-if="!rows" />
    <template v-else>
      <div class="mt-5 flex items-center gap-3">
        <h1 class="text-2xl-semibold text-ink-gray-9">{{ __("Servers") }}</h1>
        <Button variant="solid" icon-left="lucide-plus" :label="__('Order Server')" @click="order" />
      </div>
      <ViewTabs v-model="shown" :views="views" class="mt-4" />
      <p v-if="!picked.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No servers") }}</p>
      <ServerRows v-else :rows="picked" class="mt-3" />
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Button } from "frappe-ui";

import { Loading, Page, ViewTabs, __, call, followList, get, onedesk } from "../kit";
import ServerRows from "./ServerRows.vue";

const rows = ref(null);
const shown = ref("all");
const load = async () => (rows.value = await get("onedesk.one_admin.console.servers"));
const providers = computed(() => [...new Set(rows.value.map((one) => one.provider))]);
const views = computed(() => [
  { key: "all", label: __("All"), count: rows.value.length },
  ...providers.value.map((one) => ({ key: one, label: one, count: rows.value.filter((row) => row.provider === one).length })),
]);
const picked = computed(() => (shown.value === "all" ? rows.value : rows.value.filter((one) => one.provider === shown.value)));
async function order() {
  const go = await onedesk().interface.ask({
    question: __("Order a server?"),
    effect: __("Takes about 25 minutes. $24 a month."),
    verb: __("Order Server"),
  });
  if (go) await call("onedesk.one_admin.operator.order_server");
}
let timer;
let stop;
onMounted(() => {
  load();
  stop = followList("Workspace Server", load);
  timer = setInterval(load, 60000);
});
onBeforeUnmount(() => {
  clearInterval(timer);
  stop?.();
});
</script>
