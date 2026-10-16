<template>
  <!-- A project's photos and videos, its cover first, then each in turn: a
       photo for a few seconds, a video muted to its end, one video on a loop.
       The arrows and thumbnails turn it by hand, the pointer over it holds it,
       and someone who asked for less motion turns it themselves. -->
  <div class="flex flex-col gap-2">
    <div class="relative aspect-video overflow-hidden rounded-5 bg-surface-gray-2" @mouseenter="hold(true)" @mouseleave="hold(false)">
      <a :href="shown.url" target="_blank" rel="noopener" class="block size-full" :aria-label="shown.title">
        <video v-if="shown.kind === 'video'" ref="clip" :key="shown.url" :src="shown.url" class="size-full object-cover" muted playsinline :autoplay="!still" :loop="media.length === 1" @ended="on(1)" />
        <img v-else :src="shown.url" :alt="shown.title" class="size-full object-cover" />
      </a>
      <template v-if="media.length > 1">
        <Button class="absolute start-3 top-1/2 -translate-y-1/2" icon="lucide-chevron-left" :aria-label="__('Previous')" @click="on(-1)" />
        <Button class="absolute end-3 top-1/2 -translate-y-1/2" icon="lucide-chevron-right" :aria-label="__('Next')" @click="on(1)" />
        <Badge class="absolute bottom-3 end-3" :label="`${at + 1} / ${media.length}`" />
      </template>
    </div>
    <div v-if="media.length > 1" class="flex gap-2 overflow-x-auto">
      <button
        v-for="(one, index) in media"
        :key="one.url"
        type="button"
        :aria-label="one.title"
        :class="['size-14 shrink-0 overflow-hidden rounded-3', index === at ? 'ring-2 ring-outline-gray-5' : 'opacity-70 hover:opacity-100']"
        @click="at = index"
      >
        <video v-if="one.kind === 'video'" :src="`${one.url}#t=0.1`" class="size-full object-cover" muted preload="metadata" />
        <img v-else :src="one.thumbnail || one.url" alt="" class="size-full object-cover" loading="lazy" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Badge, Button } from "frappe-ui";

const props = defineProps({ media: { type: Array, required: true } });
const at = ref(0);
const shown = computed(() => props.media[at.value]);
const on = (step) => (at.value = (at.value + step + props.media.length) % props.media.length);

const PHOTO = 6000;
const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const held = ref(false);
const clip = ref(null);
let timer = null;

function hold(on) {
  held.value = on;
  if (props.media.length < 2 || !clip.value) return;
  if (on) clip.value.pause();
  else if (!still) clip.value.play().catch(() => {});
}

// A photo turns after a few seconds; a video when it ends.
watch(
  [at, held],
  () => {
    clearTimeout(timer);
    if (!still && !held.value && props.media.length > 1 && shown.value.kind !== "video") timer = setTimeout(() => on(1), PHOTO);
  },
  { immediate: true },
);
onBeforeUnmount(() => clearTimeout(timer));
</script>
