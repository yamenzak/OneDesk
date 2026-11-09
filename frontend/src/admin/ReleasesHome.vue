<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else>
      <p v-if="!said.releases.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No releases yet") }}</p>
      <template v-else>
        <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <NumberCard v-for="card in cards" :key="card.key" :title="card.title" :value="card.value" :format="count" />
        </div>
        <Section :title="__('Releases')" icon="lucide-rocket" :aside="said.releases.length">
          <Rows :rows="releases" />
        </Section>
        <Section :title="__('Servers')" icon="lucide-server" :aside="said.servers.length">
          <Rows :rows="servers" />
        </Section>
        <Section v-for="group in groups" :key="group.key" :title="group.title" :icon="group.icon" :aside="group.rows.length">
          <Rows :rows="group.rows" />
        </Section>
        <p v-if="!said.waiting.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Every workspace is on the latest release") }}</p>
      </template>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { NumberCard } from "frappe-ui/charts";

import { Loading, Page, Rows, Section, __, count, dateTime, followList, get, goTo } from "../kit";

const said = ref(null);
const load = async () => (said.value = await get("onedesk.one_admin.rollout.overview"));
load();
const stops = ["Tenant", "Workspace Server"].map((doctype) => followList(doctype, load));
onBeforeUnmount(() => stops.forEach((stop) => stop()));

const short = (release) => (release || "").slice(0, 7);
const STATES = {
  preparing: () => ({ label: __("Building"), theme: "blue" }),
  dropping: () => ({ label: __("Removing"), theme: "gray" }),
  ready: () => ({ label: __("Ready"), theme: "green" }),
};
const onLatest = computed(() => said.value.releases.filter((one) => one.current).reduce((sum, one) => sum + one.workspaces, 0));
const by = (kind) => said.value.waiting.filter((one) => one.kind === kind);
const cards = computed(() => [
  { key: "latest", title: __("On Latest Release"), value: onLatest.value },
  { key: "total", title: __("Workspaces"), value: said.value.total },
  { key: "moving", title: __("Moving Now"), value: by("moving").length },
  { key: "terms", title: __("Waiting for Terms"), value: by("terms").length },
]);
const heldOn = (one) => one.servers.map((held) => `${held.server} (${count(held.workspaces)})`).join(" · ");
const releases = computed(() =>
  said.value.releases.map((one) => ({
    key: one.release,
    label: short(one.release),
    badge: one.current ? { label: __("Current"), theme: "blue" } : STATES[one.state](),
    below: heldOn(one),
    value: count(one.workspaces),
    under: __("Workspaces"),
    progress: said.value.total ? Math.round((one.workspaces / said.value.total) * 100) : 0,
  })),
);
const benchLine = (bench) => `${short(bench.release)} · ${STATES[bench.state]().label} · ${__("{0} workspaces", [count(bench.workspaces)])}`;
const servers = computed(() =>
  said.value.servers.map((one) => ({
    key: one.server,
    label: one.server,
    lines: one.benches.map(benchLine),
    onClick: () => goTo("Form", "Workspace Server", one.name),
  })),
);
const moving = (one) => __("From {0} to {1}", [short(one.on), short(one.to)]);
const row = (one, below) => ({ key: one.name, label: one.workspace, sub: one.server, below, onClick: () => goTo("Form", "Tenant", one.name) });
const groups = computed(() =>
  [
    { key: "moving", title: __("Moving Now"), icon: "lucide-refresh-cw", rows: by("moving").map((one) => row(one, moving(one))) },
    { key: "terms", title: __("Waiting for Terms"), icon: "lucide-file-signature", rows: by("terms").map((one) => row(one, `${moving(one)} · ${__("Moves by {0}", [dateTime(one.moves_by)])}`)) },
    { key: "window", title: __("Next Windows"), icon: "lucide-calendar-clock", rows: by("window").map((one) => row(one, `${moving(one)} · ${one.at ? dateTime(one.at) : __("No window yet")}`)) },
  ].filter((group) => group.rows.length),
);
</script>
