<!-- The presenter's own screen while the audience's window plays the slideshow
     (shim/presenter.js): the slide they see, the next one, this slide's notes,
     the time, and the keys that move both. -->
<template>
	<div class="absolute inset-0 z-[60] flex flex-col bg-surface-gray-1 text-ink-gray-8" ref="root">
		<div class="flex h-12 shrink-0 items-center gap-3 border-b border-outline-gray-1 bg-surface-elevation-1 px-4">
			<span class="truncate text-base font-medium">{{ presentationDoc?.title }}</span>
			<span class="text-sm text-ink-gray-5">{{ counted }}</span>
			<div class="ms-auto flex items-center gap-3">
				<span class="text-sm text-ink-gray-5">{{ clock }}</span>
				<span class="font-mono text-lg tabular-nums">{{ elapsed }}</span>
				<Button variant="ghost" :label="running ? __('Pause') : __('Resume')" @click="toggle" />
				<Button variant="ghost" :label="__('Restart the Clock')" @click="restart" />
				<Button variant="ghost" icon-left="lucide-radio" :label="liveOn ? __('Stop Presenting Live') : __('Present Live')" @click="toggleLive" />
				<Button variant="ghost" icon-left="lucide-smartphone" :label="connected ? __('Phone Connected') : __('Phone Remote')" @click="showPhone" />
				<Button variant="solid" :label="__('End the Presentation')" @click="end" />
			</div>
		</div>

		<div v-if="ended" class="flex flex-1 items-center justify-center text-base text-ink-gray-6">
			{{ __("The audience's window was closed.") }}
		</div>
		<div v-else class="flex min-h-0 flex-1 gap-4 p-4">
			<div class="flex min-w-0 flex-[3] flex-col gap-2">
				<div class="text-sm text-ink-gray-5">{{ __("Now") }}</div>
				<div ref="nowBox" class="overflow-hidden rounded-6 border border-outline-gray-1">
					<SlidePreview v-if="now" :slide="now" :scale="nowScale" />
					<div v-else class="flex aspect-video items-center justify-center bg-surface-gray-2 text-base text-ink-gray-6">
						{{ __("End of the presentation") }}
					</div>
				</div>
				<div class="mt-auto flex items-center justify-center gap-2">
					<Button :label="__('Back')" :disabled="at <= 0" @click="go(at - 1)" />
					<Button variant="solid" :label="__('Next')" :disabled="at >= slides.length" @click="go(at + 1)" />
				</div>
			</div>
			<div class="flex min-w-0 flex-[2] flex-col gap-2">
				<div class="text-sm text-ink-gray-5">{{ __("Next") }}</div>
				<div ref="nextBox" class="overflow-hidden rounded-6 border border-outline-gray-1">
					<SlidePreview v-if="next" :slide="next" :scale="nextScale" />
					<div v-else class="flex aspect-video items-center justify-center bg-surface-gray-2 text-sm text-ink-gray-6">
						{{ __("End of the presentation") }}
					</div>
				</div>
				<div class="mt-2 flex items-center gap-2">
					<span class="text-sm text-ink-gray-5">{{ __("Speaker Notes") }}</span>
					<div class="ms-auto flex items-center gap-1">
						<Button variant="ghost" :label="__('Smaller')" @click="size = Math.max(12, size - 2)" />
						<Button variant="ghost" :label="__('Larger')" @click="size = Math.min(40, size + 2)" />
					</div>
				</div>
				<div class="min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-6 bg-surface-elevation-1 p-3" dir="auto" :style="{ fontSize: `${size}px`, lineHeight: 1.45 }">
					{{ now?.notes || __("No notes for this slide.") }}
				</div>
			</div>
		</div>
		<Dialog v-model:open="phoneOpen" :title="__('Phone Remote')" size="sm">
			<div class="flex flex-col items-center gap-3">
				<p class="text-base text-ink-gray-7">{{ __("Scan this with your phone's camera. The phone moves the slides and shows this slide's notes. To point at the slide, keep a finger on Hold to Point and turn the phone.") }}</p>
				<div v-if="paired" class="w-48 rounded-3 bg-surface-base p-2" v-html="paired.qr" />
				<a v-if="paired" class="break-all text-sm text-ink-gray-5" :href="paired.url" target="_blank" rel="noopener">{{ paired.url }}</a>
				<Badge :theme="connected ? 'green' : 'gray'" :label="connected ? __('Phone Connected') : __('Waiting for the phone…')" />
				<Button v-if="connected" variant="ghost" :label="__('Use Another Phone')" @click="anotherPhone" />
			</div>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Badge, Button, Dialog } from "frappe-ui";

import SlidePreview from "../components/SlidePreview.vue";
import { resetFocus } from "../stores/element";
import { presentationDoc } from "../stores/presentation";
import { slideIndex, slides } from "../stores/slide";
import { frame } from "./frame.js";
import { at as liveAt, beginLive, endLive, liveOn } from "./live.js";
import { connected, paired, pairPhone, tellPhone, unpairPhone } from "./phone.js";
import { link, presenting, say, unlink } from "./presenter.js";
import { __ } from "./words.js";
import { clock as clockOf, now as rightNow } from "../../kit/desk";

const root = ref(null);
const nowBox = ref(null);
const nextBox = ref(null);
const at = ref(slideIndex.value || 0);
const ended = ref(false);
const size = ref(20);

const now = computed(() => slides.value[at.value] || null);
const next = computed(() => slides.value[at.value + 1] || null);
const counted = computed(() => (at.value < slides.value.length ? __("{0} of {1}", [at.value + 1, slides.value.length]) : ""));

// each preview drawn as wide as its box
const nowScale = ref(0.5);
const nextScale = ref(0.3);
const measure = () => {
	if (nowBox.value) nowScale.value = nowBox.value.clientWidth / frame.w;
	if (nextBox.value) nextScale.value = nextBox.value.clientWidth / frame.w;
};
let watcher = null;

function go(index) {
	if (index < 0 || index > slides.value.length) return;
	at.value = index;
	say({ go: index });
}

// the phone: where it says to go, where it points, and what it is told back
const phoneOpen = ref(false);
const tellPhoneNow = () => tellPhone({ at: at.value, of: slides.value.length, notes: now.value?.notes || "", clock: clock.value, elapsed: elapsed.value });
watch(connected, (on) => on && (phoneOpen.value = false));

// everyone on the presentation's links follows this view too (shim/live.js)
watch(at, (index) => liveAt(index));
const toggleLive = () => (liveOn.value ? endLive() : beginLive(presentationDoc.value.name, at.value));

// the first phone keeps the remote, so another one needs a code of its own
function anotherPhone() {
	unpairPhone();
	showPhone();
}

async function showPhone() {
	phoneOpen.value = true;
	await pairPhone(presentationDoc.value.name, (event, payload) => {
		if (event === "hello") tellPhoneNow();
		else if (event === "go") go(at.value + (payload.step > 0 ? 1 : -1));
		else if (event === "point") say({ point: { x: +payload.x || 0, y: +payload.y || 0, on: !!payload.on } });
	});
}

// heard before anything else on the page, wherever the focus is (the
// audience's window opening takes it away); the editor underneath hears none
// of these, since an arrow would move what is chosen there
function keyed(event) {
	if (event.target?.closest?.("input, textarea, [contenteditable='true']")) return;
	if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) go(at.value + 1);
	else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) go(at.value - 1);
	else if (event.key === "Escape") end();
	else return;
	event.preventDefault();
	event.stopImmediatePropagation();
}

// the clock on the wall, and the time since the presentation began
const started = ref(Date.now());
const paused = ref(0);
const pausedAt = ref(0);
const running = computed(() => !pausedAt.value);
const tick = ref(Date.now());
let ticker = null;
const two = (n) => String(n).padStart(2, "0");
const elapsed = computed(() => {
	const ms = (pausedAt.value || tick.value) - started.value - paused.value;
	const seconds = Math.max(0, Math.floor(ms / 1000));
	const hours = Math.floor(seconds / 3600);
	return `${hours ? `${hours}:` : ""}${two(Math.floor((seconds % 3600) / 60))}:${two(seconds % 60)}`;
});
// the wall clock as the reader's desk writes a time; tick only makes it read again
const clock = computed(() => tick.value && clockOf(rightNow()));
// the phone hears each change, and the time as it goes
watch([at, () => now.value?.notes, elapsed], () => connected.value && tellPhoneNow());

function toggle() {
	if (pausedAt.value) {
		paused.value += Date.now() - pausedAt.value;
		pausedAt.value = 0;
	} else pausedAt.value = Date.now();
}

function restart() {
	started.value = Date.now();
	paused.value = 0;
	pausedAt.value = 0;
}

function end() {
	say({ end: true });
	endLive();
	unpairPhone();
	unlink();
	presenting.value = false;
}

onMounted(async () => {
	// nothing chosen underneath, so no key the editor hears first can change the slides
	resetFocus();
	link(presentationDoc.value.name, (heard) => {
		if (heard.at != null) at.value = heard.at;
		if (heard.ended) ended.value = true;
		if (heard.at != null) ended.value = false;
	});
	say({ hello: true });
	ticker = setInterval(() => (tick.value = Date.now()), 1000);
	document.addEventListener("keydown", keyed, true);
	await nextTick();
	measure();
	watcher = new ResizeObserver(measure);
	if (nowBox.value) watcher.observe(nowBox.value);
	if (nextBox.value) watcher.observe(nextBox.value);
});

onBeforeUnmount(() => {
	clearInterval(ticker);
	document.removeEventListener("keydown", keyed, true);
	watcher?.disconnect();
	endLive();
	unpairPhone();
	unlink();
});
</script>
