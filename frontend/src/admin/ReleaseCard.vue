<template>
  <article class="flex flex-col gap-3 rounded-4 border border-outline-gray-1 bg-surface-elevation-1 p-4">
    <div class="flex items-start justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <span class="lucide-git-commit-horizontal size-5 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <div class="min-w-0">
          <h3 class="truncate text-lg font-semibold text-ink-gray-9" :title="release.subject || ''">{{ release.subject || __("Release {0}", [short]) }}</h3>
          <p class="flex min-w-0 items-center gap-1 text-sm text-ink-gray-5">
            <a v-if="link" :href="link" target="_blank" rel="noopener" class="font-mono hover:underline">{{ short }}</a>
            <span v-else class="font-mono">{{ short }}</span>
            <span v-if="release.committed_at" class="truncate">· {{ __("Committed {0}", [ago(release.committed_at)]) }}</span>
          </p>
        </div>
      </div>
      <Badge :label="state.label" :theme="state.theme" size="md" />
    </div>

    <Figures :figures="figures" :columns="3" bare class="!grid-cols-3" />

    <Progress v-if="total" :value="Math.round((release.workspaces / total) * 100)" size="sm" />

    <p v-if="release.prepared_in" class="text-sm text-ink-gray-5">{{ __("Put on its servers in {0}", [duration(release.prepared_in, { seconds: false })]) }}</p>

    <div v-if="release.servers.length" class="border-t border-outline-gray-1 pt-1">
      <Rows :rows="servers" />
    </div>

    <div v-if="release.held.length" class="flex min-w-0 items-center gap-2 text-sm text-ink-gray-5">
      <div class="flex -space-x-1" :title="names">
        <Avatar v-for="one in shown" :key="one.name" :label="one.workspace" shape="square" size="sm" />
      </div>
      <span class="truncate">{{ names }}</span>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Badge, Progress } from "frappe-ui";

import { Figures, Rows, __, ago, count, date, duration, goTo } from "../kit";

const SHOWN = 5;

const props = defineProps({ release: { type: Object, required: true }, total: { type: Number, default: 0 }, repository: { type: String, default: "" } });

const STATES = {
  preparing: () => ({ label: __("Building"), theme: "blue" }),
  dropping: () => ({ label: __("Removing"), theme: "gray" }),
  ready: () => ({ label: __("Ready"), theme: "green" }),
};
const short = computed(() => (props.release.release || "").slice(0, 7));
const link = computed(() => (props.repository && /^[0-9a-f]{40}$/.test(props.release.release) ? `https://github.com/${props.repository}/commit/${props.release.release}` : ""));
const state = computed(() => {
  if (props.release.state !== "ready") return STATES[props.release.state]();
  return props.release.current ? { label: __("Current"), theme: "blue" } : { label: __("Older"), theme: "gray" };
});
const built = computed(() => props.release.built_at || props.release.ready_at);
const figures = computed(() => [
  { title: __("Workspaces"), value: count(props.release.workspaces) },
  { title: __("Built"), value: built.value ? date(built.value) : "–" },
  { title: __("Build Time"), value: props.release.built_in ? duration(props.release.built_in, { seconds: false }) : "–" },
]);
const servers = computed(() =>
  props.release.servers.map((one) => ({
    key: one.server,
    label: one.server,
    badge: one.state === "ready" ? null : STATES[one.state](),
    value: count(one.workspaces),
    under: __("Workspaces"),
    onClick: () => goTo("Form", "Workspace Server", one.server),
  })),
);
const shown = computed(() => props.release.held.slice(0, SHOWN));
const names = computed(() => props.release.held.map((one) => one.workspace).join(", "));
</script>
