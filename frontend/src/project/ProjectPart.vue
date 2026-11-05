<template>
  <div class="text-ink-gray-8">
    <Loading v-if="!said" />
    <Overview v-else-if="part === 'overview'" :said="said" data-tour="oneproject-overview" @changed="load" @view="opens" />
    <div v-else-if="part === 'money'" class="flex flex-col gap-8">
      <Money v-if="allowed('money')" :said="said" @changed="load" @view="opens" />
      <Invoices v-if="allowed('invoices')" :project-name="said.name" :project-title="said.title" :kind="said.kind" :customer="said.customer" :currency="said.currency" />
    </div>
    <Time v-else-if="part === 'time'" :project-name="said.name" :customer="said.customer" :title="said.title" :tree="said.parts || [said.name]" />
    <Suppliers v-else-if="part === 'suppliers'" :said="said" />
    <Team v-else-if="part === 'team'" :project-name="said.name" :modified="said.modified" @changed="load" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { Loading, call, follow, followList, listen } from "../kit";
import Invoices from "./Invoices.vue";
import Money from "./Money.vue";
import Overview from "./Overview.vue";
import Suppliers from "./Suppliers.vue";
import Team from "./Team.vue";
import Time from "./Time.vue";
import { provideParts } from "./parts";

const props = defineProps({
  project: { type: String, required: true },
  part: { type: String, required: true },
  field: { type: String, required: true },
  frm: { type: Object, default: null },
});

const TABS = { money: "costing_tab", invoices: "costing_tab", time: "one_time_tab", suppliers: "one_suppliers_tab", team: "users_tab", tasks: "tasks_tab", board: "tasks_tab", timeline: "tasks_tab", overview: "overview_tab" };

const said = ref(null);
provideParts(computed(() => said.value?.parts || null));

const allowed = (key) => key === "team" || !!said.value?.views.includes(key);
const shown = () => (props.part === "overview" ? true : props.part === "money" ? allowed("money") || allowed("invoices") : allowed(props.part));

function opens(view) {
  const tab = TABS[view];
  if (tab && props.frm?.layout) props.frm.layout.select_tab(tab);
}

async function load() {
  const asked = props.project;
  const shared = props.frm ? (props.frm.one_project_said ||= {}) : {};
  if (shared.name !== asked || Date.now() - shared.at > 1500) {
    shared.name = asked;
    shared.at = Date.now();
    shared.got = call("onedesk.one_project.view.said", { project: asked });
  }
  const got = await shared.got;
  if (asked !== props.project) return;
  said.value = got;
  props.frm?.toggle_display(props.field, shown());
}

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
};
let stop = [];
watch(
  () => props.project,
  (now) => {
    stop.forEach((one) => one());
    said.value = null;
    stop = [
      follow("Project", now, load),
      listen("one_project_money", (data) => data.project === now && load()),
      ...["Sales Order", "Quotation", "Employee", "User"].map((one) => followList(one, soon)),
    ];
    load();
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
</script>
