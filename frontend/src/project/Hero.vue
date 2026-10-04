<template>
  <!-- The project's Featured Media across the top of its page, the cover
       first, then each photo and video in turn: a photo for a few seconds,
       slowly drawing in, a video muted to its end. The name sits over it.
       Holding the pointer over it pauses it; a click opens the viewer. -->
  <div class="group relative h-72 overflow-hidden rounded-7 bg-surface-gray-9 lg:h-[22rem]" @mouseenter="held = true" @mouseleave="held = false">
    <button class="absolute inset-0 block" :aria-label="__('Featured Media')" @click="$emit('open', at)">
      <div v-for="(one, i) in media" :key="one.name" class="absolute inset-0 transition-opacity duration-1000 motion-reduce:transition-none" :class="i === at ? 'opacity-100' : 'opacity-0'">
        <video
          v-if="one.kind === 'video'"
          :ref="(el) => (videos[i] = el)"
          :src="one.url"
          class="size-full object-cover"
          muted
          playsinline
          :loop="media.length === 1"
          preload="metadata"
          @timeupdate="(e) => i === at && (shown = e.target.duration ? e.target.currentTime / e.target.duration : 0)"
          @ended="i === at && next()"
        />
        <img v-else :src="one.url" :alt="one.title" class="size-full object-cover transition-transform duration-[7000ms] ease-linear" :class="i === at && !still ? 'scale-[1.06]' : 'scale-100'" />
      </div>
    </button>
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black-overlay-800 via-black-overlay-300 via-35% to-transparent to-65%" />
    <div class="pointer-events-none absolute inset-x-0 top-0 h-1/4 bg-gradient-to-b from-black-overlay-300 to-transparent" />

    <div v-if="media.length > 1" class="pointer-events-none absolute inset-x-6 top-5 flex gap-1.5 lg:inset-x-8">
      <span v-for="(one, i) in media" :key="one.name" class="h-0.5 flex-1 overflow-hidden rounded-full bg-white-overlay-300">
        <span class="block h-full rounded-full bg-white" :style="{ width: `${i < at ? 100 : i === at ? Math.round(shown * 100) : 0}%` }" />
      </span>
    </div>

    <div class="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between gap-6 p-6 lg:p-8">
      <div class="pointer-events-auto min-w-0"><slot name="over" /></div>
      <div class="pointer-events-auto flex shrink-0 items-center gap-3 max-sm:hidden">
        <div v-if="media.length > 1" class="flex -space-x-3">
          <button v-for="one in upcoming" :key="one.name" class="size-11 overflow-hidden rounded-4 ring-2 ring-white-overlay-900 transition hover:-translate-y-0.5" :aria-label="one.title" @click="go(media.indexOf(one))">
            <Thumb :item="one" />
          </button>
        </div>
        <button class="flex h-9 items-center gap-2 rounded-5 border border-white-overlay-200 bg-black-overlay-400 px-3 text-base font-medium text-white backdrop-blur-md hover:bg-black-overlay-600" @click="$emit('open', at)">
          <span class="lucide-images size-4" />{{ media.length > 1 ? __("View All {0}", [media.length]) : __("View") }}
        </button>
      </div>
    </div>
    <button v-if="canAdd" class="absolute end-4 top-9 flex h-8 items-center gap-1.5 rounded-5 border border-white-overlay-200 bg-black-overlay-400 px-2.5 text-sm font-medium text-white opacity-0 backdrop-blur-md transition hover:bg-black-overlay-600 group-hover:opacity-100 lg:end-6" @click="$emit('add')">
      <span class="lucide-image-plus size-4" />{{ __("Add Photos") }}
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { __, lessMotion } from "../kit";
import Thumb from "./Thumb.vue";

const props = defineProps({ media: { type: Array, required: true }, canAdd: Boolean });
defineEmits(["open", "add"]);

// How long a photo stays.
const PHOTO = 6000;
// Someone who asked their system for less motion gets the photos still and
// turns them themselves.
const still = lessMotion();

const at = ref(0);
const shown = ref(0);
const held = ref(false);
const videos = ref([]);
const upcoming = computed(() => [1, 2, 3].map((k) => props.media[(at.value + k) % props.media.length]).filter((one, k, all) => one && props.media.length > k + 1 && all.indexOf(one) === k));

function go(i) {
  at.value = (i + props.media.length) % props.media.length;
}
const next = () => props.media.length > 1 && go(at.value + 1);

// The one shown plays, from the start; the rest wait.
async function play() {
  shown.value = 0;
  await nextTick();
  videos.value.forEach((el, i) => {
    if (!el) return;
    if (i === at.value) {
      el.currentTime = 0;
      el.play().catch(() => {});
    } else el.pause();
  });
}
watch(at, play);
watch(() => props.media.length, (n) => at.value >= n && (at.value = 0));

// A photo's time runs while nobody holds it; a video's is its own.
let frame = null;
let last = null;
function tick(now) {
  const one = props.media[at.value];
  if (last !== null && one?.kind === "photo" && !held.value && !still && props.media.length > 1) {
    shown.value += (now - last) / PHOTO;
    if (shown.value >= 1) next();
  }
  last = now;
  frame = requestAnimationFrame(tick);
}
watch(held, (now) => {
  const el = videos.value[at.value];
  if (el) now && props.media.length > 1 ? el.pause() : el.play().catch(() => {});
});
onMounted(() => {
  play();
  frame = requestAnimationFrame(tick);
});
onBeforeUnmount(() => cancelAnimationFrame(frame));
</script>
