<!-- The rulers along the slide's top and side edges, and the presentation's
     guides across it (shim/guides.js). Drawn on screen over the canvas, so they
     follow the slide as it is panned and zoomed without being scaled with it.
     A guide is dragged out of a ruler, moved by dragging, and dropped off the
     slide to remove it. -->
<template>
	<div v-if="rulersShown" ref="root" class="pointer-events-none absolute inset-0 overflow-hidden">
		<div
			class="absolute border-b border-outline-gray-2 bg-surface-elevation-1"
			:class="readonly ? '' : 'pointer-events-auto cursor-row-resize'"
			:style="{ left: `${place.left}px`, top: `${place.top - BAND}px`, width: `${place.width}px`, height: `${BAND}px` }"
			@pointerdown="(e) => fromRuler(e, 'y')"
			@pointermove="dragging"
			@pointerup="dropped"
		>
			<div v-for="tick in ticks.x" :key="`x${tick.at}`" class="absolute bottom-0 border-s border-outline-gray-3" :style="{ insetInlineStart: `${tick.px}px`, height: tick.major ? '8px' : '4px' }">
				<span v-if="tick.major" class="absolute -top-3 start-1 text-2xs text-ink-gray-5">{{ tick.label }}</span>
			</div>
		</div>
		<div
			class="absolute border-e border-outline-gray-2 bg-surface-elevation-1"
			:class="readonly ? '' : 'pointer-events-auto cursor-col-resize'"
			:style="{ left: `${place.left - BAND}px`, top: `${place.top}px`, width: `${BAND}px`, height: `${place.height}px` }"
			@pointerdown="(e) => fromRuler(e, 'x')"
			@pointermove="dragging"
			@pointerup="dropped"
		>
			<div v-for="tick in ticks.y" :key="`y${tick.at}`" class="absolute end-0 border-t border-outline-gray-3" :style="{ top: `${tick.px}px`, width: tick.major ? '8px' : '4px' }">
				<span v-if="tick.major" class="absolute end-2.5 top-1 rotate-180 text-2xs leading-none text-ink-gray-5 [writing-mode:vertical-rl]">{{ tick.label }}</span>
			</div>
		</div>

		<div
			v-for="guide in guides"
			:key="guide.id"
			class="absolute flex"
			:class="[readonly ? '' : guide.axis === 'x' ? 'pointer-events-auto cursor-col-resize' : 'pointer-events-auto cursor-row-resize', guide.axis === 'x' ? 'justify-center' : 'flex-col justify-center']"
			:style="lineStyle(guide)"
			:title="readonly ? '' : __('Drag off the slide to remove')"
			@pointerdown="(e) => grab(e, guide)"
			@pointermove="dragging"
			@pointerup="dropped"
		>
			<div :class="[guide.axis === 'x' ? 'h-full border-s' : 'w-full border-t', held === guide.id && off ? 'border-dashed border-outline-gray-4' : 'border-outline-cyan-6']" />
		</div>

		<div v-if="held" class="absolute rounded-4 bg-surface-base px-1.5 py-0.5 text-xs text-ink-gray-8 ring-1 ring-outline-gray-2" :style="{ left: `${pointer.x + 12}px`, top: `${pointer.y + 12}px` }">
			{{ off ? __("Remove") : count(heldAt) }}
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { inReadonlyMode } from "../stores/presentation";
import { slideBounds } from "../stores/slide";
import { frame } from "./frame.js";
import { addGuide, guides, moveGuide, rulersShown } from "./guides.js";
import { __ } from "./words.js";
import { count } from "../../kit/desk";

// how thick a ruler is, and how far a guide's grip reaches either side of it
const BAND = 18;
const GRIP = 3;
// the steps a ruler counts in, in slide units; the first that leaves room for a number
const STEPS = [10, 20, 25, 50, 100, 200, 250, 500, 1000];

const root = ref(null);
const readonly = computed(() => inReadonlyMode.value);
const origin = reactive({ left: 0, top: 0 });

// where the slide sits within this layer
const place = computed(() => ({
	left: (slideBounds.left || 0) - origin.left,
	top: (slideBounds.top || 0) - origin.top,
	width: slideBounds.width || 0,
	height: slideBounds.height || 0,
}));
const scale = computed(() => slideBounds.scale || 1);

const ticks = computed(() => {
	const step = STEPS.find((one) => one * scale.value >= 48) || STEPS[STEPS.length - 1];
	const minor = step / 5;
	const along = (length) => {
		const out = [];
		for (let at = 0; at <= length; at += minor) {
			const major = Math.round(at / minor) % 5 === 0;
			out.push({ at, px: at * scale.value, major, label: major ? count(at) : "" });
		}
		return out;
	};
	return { x: along(frame.w), y: along(frame.h) };
});

// a guide reaches a little past the slide's edges, so it can be taken hold of there
function lineStyle(guide) {
	const reach = BAND;
	if (guide.axis === "x")
		return {
			left: `${Math.round(place.value.left + guide.at * scale.value) - GRIP}px`,
			top: `${place.value.top - reach}px`,
			width: `${GRIP * 2 + 1}px`,
			height: `${place.value.height + reach * 2}px`,
		};
	return {
		left: `${place.value.left - reach}px`,
		top: `${Math.round(place.value.top + guide.at * scale.value) - GRIP}px`,
		width: `${place.value.width + reach * 2}px`,
		height: `${GRIP * 2 + 1}px`,
	};
}

// the guide in hand, where it is, and whether letting go now removes it
const held = ref("");
const heldAxis = ref("x");
const heldAt = ref(0);
const pointer = reactive({ x: 0, y: 0 });
const off = computed(() => heldAt.value < 0 || heldAt.value > (heldAxis.value === "x" ? frame.w : frame.h));

function at(event, axis) {
	const rect = root.value.getBoundingClientRect();
	pointer.x = event.clientX - rect.left;
	pointer.y = event.clientY - rect.top;
	return axis === "x" ? (event.clientX - slideBounds.left) / scale.value : (event.clientY - slideBounds.top) / scale.value;
}

function take(event, id, axis) {
	event.preventDefault();
	event.stopPropagation();
	event.currentTarget.setPointerCapture(event.pointerId);
	held.value = id;
	heldAxis.value = axis;
}

function fromRuler(event, axis) {
	if (readonly.value || event.button !== 0) return;
	const where = Math.max(0, Math.min(at(event, axis), axis === "x" ? frame.w : frame.h));
	const id = addGuide(axis, where);
	if (!id) return;
	heldAt.value = where;
	take(event, id, axis);
}

function grab(event, guide) {
	if (readonly.value || event.button !== 0) return;
	heldAt.value = at(event, guide.axis);
	take(event, guide.id, guide.axis);
}

function dragging(event) {
	if (!held.value) return;
	heldAt.value = at(event, heldAxis.value);
	moveGuide(held.value, heldAt.value);
}

function dropped(event) {
	if (!held.value) return;
	moveGuide(held.value, at(event, heldAxis.value), true);
	held.value = "";
}

// the layer's own place on screen, measured again whenever the window or the panels around it change
const measure = () => {
	const rect = root.value?.getBoundingClientRect();
	if (rect) Object.assign(origin, { left: rect.left, top: rect.top });
};
let watcher = null;
const observe = async () => {
	watcher?.disconnect();
	await nextTick();
	if (!root.value) return;
	measure();
	watcher = new ResizeObserver(measure);
	watcher.observe(root.value);
};
watch(rulersShown, (shown) => shown && observe());
watch(() => [slideBounds.left, slideBounds.top], measure);
onMounted(observe);
onBeforeUnmount(() => watcher?.disconnect());
</script>
