<template>
  <Figures :figures="figures" :columns="Math.min(4, figures.length)" />
</template>

<script setup>
import { computed } from "vue";

import Figures from "../kit/Figures.vue";

// A record's head: at most four figures its module declares
// (ready.MODULES "cards"), drawn by the kit's Figures, the same card the
// module homes use, so a figure looks the same wherever it is shown.
const props = defineProps({ cards: { type: Array, default: () => [] } });

const figures = computed(() =>
  props.cards.slice(0, 4).map((card) => ({
    title: card.title,
    value: card.value,
    note: card.note || undefined,
    bar: card.bar ?? undefined,
    route: card.route,
    alarm: card.tone === "red",
    ...(card.series?.length
      ? {
          sparkline: { data: card.series, type: card.type || "bar" },
          ...(card.delta != null ? { delta: card.delta, deltaFormat: (value) => `${value}%`, note: card.deltaCaption } : {}),
        }
      : {}),
  }))
);
</script>
