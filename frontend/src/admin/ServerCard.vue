<template>
  <article class="flex cursor-pointer flex-col gap-3 rounded-4 border border-outline-gray-1 bg-surface-elevation-1 p-4 hover:border-outline-gray-3" role="link" tabindex="0" @click="open" @keydown.enter="open">
    <div class="flex items-start justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <Mark v-if="server.provider" :name="server.provider.toLowerCase().replaceAll(' ', '-')" class="size-5" />
        <div class="min-w-0">
          <h3 class="truncate text-lg font-semibold text-ink-gray-9">{{ server.server }}</h3>
          <p class="truncate text-sm text-ink-gray-5">{{ where }}</p>
        </div>
      </div>
      <Badge :label="__(server.status)" :theme="STATUS[server.status] || 'gray'" size="md" />
    </div>

    <Figures :figures="meters" :columns="3" bare class="!grid-cols-3" />

    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-outline-gray-1 pt-3 text-sm text-ink-gray-5">
      <div class="flex min-w-0 items-center gap-2">
        <div v-if="shown.length" class="flex -space-x-1" :title="names">
          <Avatar v-for="one in shown" :key="one.slug" :label="one.name" shape="square" size="sm" />
        </div>
        <span class="truncate">{{ held }}</span>
      </div>
      <span class="truncate tabular-nums">{{ release }}</span>
    </div>
    <p v-if="facts" class="text-sm text-ink-gray-5" :title="__('In the last 24 hours')">{{ facts }}</p>
  </article>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Badge } from "frappe-ui";

import { Figures, Mark, __, count, get, goTo } from "../kit";

const STATUS = { Up: "green", "Filling Up": "amber", Full: "amber", Down: "red", Connecting: "blue", Releasing: "amber", Released: "gray" };
const LOW_BURST = 20;

const props = defineProps({
  server: { type: Object, required: true },
  tick: { type: Number, default: 0 },
  requests: { type: Number, default: null },
  hue: { type: Function, required: true },
});

const reading = ref(null);
const load = async () => {
  reading.value = await get("onedesk.one_admin.metrics.card", { server: props.server.server }).catch(() => null);
};
load();
watch(() => props.tick, load);

const open = () => goTo("Form", "Workspace Server", props.server.server);
const share = (value) => `${Math.round(value)}%`;
const at = (values) => (values || []).filter((one) => one !== null && one !== undefined).at(-1) ?? null;

const meter = (title, values, fallback, limit, color) => {
  const value = at(values) ?? fallback ?? null;
  return { title, value: value === null ? null : share(value), alarm: Boolean(limit && value >= limit), sparkline: values?.length ? { data: values, type: "area", color } : undefined };
};
const meters = computed(() => [
  meter(__("CPU"), reading.value?.cpu, null, null, props.hue(2)),
  meter(__("Memory"), reading.value?.memory, props.server.memory, props.server.memory_limit, props.hue(0)),
  meter(__("Disk"), reading.value?.disk, props.server.disk, props.server.disk_limit, props.hue(4)),
]);

const where = computed(() => [props.server.provider, props.server.region].filter(Boolean).join(" · "));
const shown = computed(() => props.server.workspaces.slice(0, 4));
const names = computed(() => props.server.workspaces.map((one) => one.name).join(", "));
const held = computed(() => (props.server.capacity ? __("{0} of {1} Workspaces", [count(props.server.held), count(props.server.capacity)]) : __("{0} Workspaces", [count(props.server.held)])));
const release = computed(() => {
  if (props.server.coming) return __("Updating to {0}", [props.server.coming]);
  return props.server.release ? __("Release {0}", [props.server.release]) : "–";
});
const facts = computed(() => {
  const out = [];
  if (props.requests !== null) out.push(__("{0} Requests", [count(props.requests)]));
  const burst = reading.value?.burst;
  if (burst !== null && burst !== undefined) out.push(burst < LOW_BURST ? __("CPU Burst Low ({0})", [share(burst)]) : __("CPU Burst {0}", [share(burst)]));
  return out.join(" · ");
});
</script>
