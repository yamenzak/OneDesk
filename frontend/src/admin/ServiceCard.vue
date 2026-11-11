<template>
  <article class="flex cursor-pointer flex-col gap-3 rounded-4 border bg-surface-elevation-1 p-4 hover:border-outline-gray-3" :class="chosen ? 'border-outline-gray-4' : 'border-outline-gray-1'" role="button" tabindex="0" :aria-pressed="chosen" @click="$emit('open')" @keydown.enter="$emit('open')">
    <div class="flex items-start justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <span :class="ICONS[service.service] || 'lucide-activity'" class="size-5 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <div class="min-w-0">
          <h3 class="truncate text-lg font-semibold text-ink-gray-9">{{ __(service.service) }}</h3>
          <p class="truncate text-sm text-ink-gray-5">{{ checked }}</p>
        </div>
      </div>
      <Badge :label="__(service.state)" :theme="THEMES[service.state] || 'gray'" size="md" />
    </div>

    <Figures :figures="figures" :columns="2" bare class="!grid-cols-2" />

    <div class="flex h-7 items-stretch gap-px" :aria-label="__('Last 30 Days')">
      <span v-for="day in service.strip" :key="day.day" class="flex-1 rounded-1" :class="tone(day.share)" :title="said(day)" />
    </div>

    <p v-if="service.detail" class="line-clamp-2 border-t border-outline-gray-1 pt-3 text-sm" :class="service.state === 'Failing' ? 'text-ink-red-5' : 'text-ink-gray-5'">{{ service.detail }}</p>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { Badge } from "frappe-ui";

import { Figures, __, ago, count, shortDate } from "../kit";

const THEMES = { Working: "green", Failing: "red", "Not Set Up": "gray" };
const ICONS = {
  Cloudflare: "lucide-cloud",
  "Edge Router": "lucide-route",
  R2: "lucide-hard-drive",
  Keeper: "lucide-archive",
  "AI Gateway": "lucide-sparkles",
  Mail: "lucide-mail",
  Sending: "lucide-send",
  Stripe: "lucide-credit-card",
  Workspaces: "lucide-building-2",
  Backups: "lucide-database-backup",
};
const SOME = 5;
const MOST = 50;

const props = defineProps({ service: { type: Object, required: true }, hue: { type: Function, required: true }, chosen: Boolean });
defineEmits(["open"]);

const checked = computed(() => (props.service.checked_at ? __("Checked {0}", [ago(props.service.checked_at)]) : __("Not checked yet")));
const answered = computed(() => props.service.trend.filter((one) => one !== null));
const figures = computed(() => [
  { title: __("Uptime, 30 Days"), value: props.service.uptime === null ? "–" : `${props.service.uptime}%`, alarm: props.service.uptime !== null && props.service.uptime < 99 },
  {
    title: __("Time to Answer"),
    value: props.service.took === null ? "–" : __("{0} ms", [count(props.service.took)]),
    sparkline: answered.value.length > 1 ? { data: answered.value, type: "area", color: props.hue(0) } : undefined,
  },
]);
const tone = (share) => {
  if (share === null || share === undefined) return "bg-surface-gray-3";
  if (share >= MOST) return "bg-surface-red-5";
  return share >= SOME ? "bg-surface-amber-5" : "bg-surface-green-5";
};
const said = (day) => {
  const when = shortDate(day.day);
  if (day.share === null || day.share === undefined) return __("{0}: Not checked", [when]);
  return __("{0}: {1}% of checks failed", [when, day.share]);
};
</script>
