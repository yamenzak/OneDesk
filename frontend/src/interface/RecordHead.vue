<template>
  <Figures :figures="figures" :columns="Math.min(4, figures.length)" class="[&_.text-3xl-semibold>span:first-child]:min-w-0 [&_.text-3xl-semibold>span:first-child]:shrink [&_.text-3xl-semibold>span:first-child]:[overflow-wrap:anywhere]" />
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
