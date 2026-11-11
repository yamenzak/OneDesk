<template>
  <Page wide>
    <Loading v-if="!said" />
    <div v-else class="pb-4">
      <div class="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <NumberCard v-for="card in cards" :key="card.key" :title="card.title" :value="card.value" :format="card.format || count" />
      </div>

      <p v-if="!said.releases.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("No releases yet") }}</p>
      <template v-else>
        <Section :title="__('Releases')" icon="lucide-rocket" :aside="said.releases.length">
          <div class="grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
            <ReleaseCard v-for="one in said.releases" :key="one.release" :release="one" :total="said.total" :repository="said.repository" />
          </div>
        </Section>


        <Section v-for="group in groups" :key="group.key" :title="group.title" :icon="group.icon" :aside="group.rows.length">
          <Rows :rows="group.rows" />
        </Section>
        <p v-if="!said.waiting.length" class="py-6 text-center text-base text-ink-gray-5">{{ __("Every workspace is on the latest release") }}</p>
      </template>
    </div>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { NumberCard } from "frappe-ui/charts";

import { Loading, Page, Rows, Section, __, ago, count, dateTime, followList, get, goTo } from "../kit";
import ReleaseCard from "./ReleaseCard.vue";

const said = ref(null);
const load = async () => (said.value = await get("onedesk.one_admin.rollout.overview"));
load();
const stops = ["Tenant", "Workspace Server"].map((doctype) => followList(doctype, load));
onBeforeUnmount(() => stops.forEach((stop) => stop()));

const short = (release) => (release || "").slice(0, 7);
const latest = computed(() => said.value.releases.find((one) => one.current));
const onLatest = computed(() => said.value.releases.filter((one) => one.current).reduce((sum, one) => sum + one.workspaces, 0));
const by = (kind) => said.value.waiting.filter((one) => one.kind === kind);
const cards = computed(() => [
  { key: "latest", title: __("On Latest Release"), value: said.value.total && latest.value ? `${Math.round((100 * onLatest.value) / said.value.total)}%` : "–", format: (value) => value },
  { key: "released", title: __("Latest Release"), value: latest.value ? ago(latest.value.built_at || latest.value.ready_at) || short(latest.value.release) : "–", format: (value) => value },
  { key: "moving", title: __("Moving Now"), value: by("moving").length },
  { key: "waiting", title: __("Waiting for a Window"), value: by("window").length + by("terms").length },
]);

const moving = (one) => __("From {0} to {1}", [short(one.on), short(one.to)]);
const row = (one, below, badge) => ({ key: one.name, label: one.workspace, sub: one.server, below, badge, onClick: () => goTo("Form", "Tenant", one.name) });
const groups = computed(() =>
  [
    { key: "moving", title: __("Moving Now"), icon: "lucide-refresh-cw", rows: by("moving").map((one) => row(one, moving(one), { label: __("Moving"), theme: "blue" })) },
    {
      key: "terms",
      title: __("Waiting for Terms"),
      icon: "lucide-file-signature",
      rows: by("terms").map((one) => row(one, `${moving(one)} · ${__("Moves by {0}", [dateTime(one.moves_by)])}`, { label: __("Terms"), theme: "amber" })),
    },
    { key: "window", title: __("Next Windows"), icon: "lucide-calendar-clock", rows: by("window").map((one) => row(one, `${moving(one)} · ${one.at ? dateTime(one.at) : __("No window yet")}`)) },
  ].filter((group) => group.rows.length),
);
</script>
