<!-- A widget drawn small, in its look, for Add a Widget and the canvas:
     what it will show, with example words, sized in em from its own box as
     the screen sizes it (one_display/widgets.py PRESETS). One's own;
     VENDORED.md. -->
<template>
	<div class="flex size-full flex-col items-center justify-center overflow-hidden text-center leading-tight" :style="dressed">
		<template v-if="type === 'Clock'">
			<span class="font-semibold tabular-nums" :style="em(2.6)">{{ settings.hours === "12" ? "9:41" : "09:41" }}</span>
			<span v-if="settings.date !== 0" class="opacity-80" :style="em(0.8)">{{ shown }}</span>
		</template>
		<span v-else-if="type === 'Text'" class="w-full font-semibold" :style="{ fontSize: frameHigh ? `${((settings.size || 5) / 100) * frameHigh}px` : `${settings.size || 5}cqh`, textAlign: align, padding: '0 0.3em' }">{{ settings.text || __("Text") }}</span>
		<div v-else-if="type === 'Ticker'" class="w-full truncate whitespace-nowrap text-start" :style="{ ...em(2.6), padding: '0 0.3em' }">{{ __("Latest news") }} &nbsp;•&nbsp; {{ __("Opening hours") }} &nbsp;•&nbsp; {{ __("Welcome") }}</div>
		<div v-else-if="type === 'Queue Board'" class="flex w-full flex-col text-start" :style="{ gap: '0.3em', padding: '0.4em' }">
			<span class="uppercase opacity-70" :style="em(0.7)">{{ __("Now Serving") }}</span>
			<div class="flex items-baseline justify-between" :style="{ ...chip, borderRadius: '0.3em', padding: '0.2em 0.5em' }">
				<span class="font-bold" :style="em(1.6)">A012</span><span class="whitespace-nowrap" :style="em(0.8)">{{ __("Counter {0}", [2]) }}</span>
			</div>
			<div v-for="one in ['B007', 'A011']" :key="one" class="flex justify-between whitespace-nowrap" :style="em(0.9)"><span class="font-semibold">{{ one }}</span><span class="opacity-70">{{ __("Counter {0}", [1]) }}</span></div>
		</div>
		<div v-else-if="type === 'Kiosk'" class="flex w-full flex-col items-center" :style="{ gap: '0.4em', padding: '0.5em' }">
			<span class="font-semibold" :style="em(1.1)">{{ __("Take a ticket") }}</span>
			<span v-for="one in [__('Enquiries'), __('Payments'), __('Collections')]" :key="one" class="w-4/5" :style="{ ...chip, ...em(0.8), borderRadius: '0.3em', padding: '0.25em 0' }">{{ one }}</span>
		</div>
		<template v-else-if="type === 'Weather'">
			<span class="flex items-center font-semibold" :style="{ ...em(2), gap: '0.2em' }"><Icon icon="lucide-sun" :style="square(0.9)" />24°</span>
			<span v-if="settings.days !== 0" class="flex opacity-80" :style="{ ...em(0.7), gap: '0.6em', marginTop: '0.2em' }"><span v-for="day in Math.min(settings.days ?? 3, 5)" :key="day">{{ 26 - day }}°</span></span>
		</template>
		<div v-else-if="type === 'Board'" class="grid size-full" :style="{ gap: '0.3em', padding: '0.4em', gridTemplateColumns: `repeat(${settings.columns || 3}, minmax(0, 1fr))` }">
			<span v-for="one in (settings.columns || 3) * 2" :key="one" class="flex items-end" :style="{ ...chip, ...em(0.6), borderRadius: '0.3em', padding: '0.2em', opacity: [1, 0.55, 0.8, 0.4, 0.9, 0.65, 1, 0.5][one % 8] }">{{ one }}</span>
		</div>
		<template v-else-if="type === 'Board Item'">
			<span class="font-semibold" :style="em(1.4)">{{ __("Room {0}", [1]) }}</span>
			<span class="rounded-full" :style="{ ...chip, ...em(0.8), marginTop: '0.3em', padding: '0 0.6em' }">{{ __("Free") }}</span>
		</template>
		<img v-else-if="type === 'Image' && settings.image" :src="settings.image" alt="" class="size-full" :class="settings.fit === 'cover' ? 'object-cover' : 'object-contain'" />
		<Icon v-else-if="type === 'Image'" icon="lucide-image" class="opacity-70" :style="square(2.4)" />
		<template v-else-if="type === 'QR Code'">
			<Icon icon="lucide-qr-code" :style="square(3)" />
			<span v-if="settings.caption" :style="{ ...em(0.7), marginTop: '0.2em' }">{{ settings.caption }}</span>
		</template>
		<template v-else-if="type === 'Custom'">
			<span v-if="custom === 'countdown'" class="font-semibold tabular-nums" :style="em(1.8)">12 : 04 : 37</span>
			<div v-else-if="custom === 'progress'" class="w-full" :style="{ padding: '0 0.6em' }">
				<div class="flex justify-between" :style="em(0.8)"><span>{{ __("Progress") }}</span><span>64 / 100</span></div>
				<div class="overflow-hidden rounded-full" :style="{ height: '0.6em', marginTop: '0.3em', background: 'currentColor', opacity: 0.25 }" />
				<div class="rounded-full" :style="{ height: '0.6em', width: '64%', marginTop: '-0.6em', background: 'currentColor' }" />
			</div>
			<span v-else-if="custom === 'rotating_messages'" class="font-semibold" :style="em(1.4)">{{ __("Welcome") }}</span>
			<Icon v-else icon="lucide-code" class="opacity-70" :style="square(2.4)" />
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Icon } from "frappe-ui";
import { date, today } from "../../kit/desk";
import { __ } from "./words.js";

const props = defineProps({
	type: { type: String, required: true },
	preset: { type: String, default: "" },
	settings: { type: Object, default: () => ({}) },
	look: { type: Object, default: () => ({}) },
	// the business's colour and the words on it, as the Accent look wears them
	brand: { type: String, default: "" },
	onBrand: { type: String, default: "" },
	// how many of the editor's units one card pixel is, for the look's lengths
	scale: { type: Number, default: 1 },
	// on the canvas a Text widget's size is a share of the screen's height
	frameHigh: { type: Number, default: 0 },
});

const em = (size) => ({ fontSize: `${size}em` });
const square = (size) => ({ width: `${size}em`, height: `${size}em` });
const chip = computed(() => ({ background: props.brand || undefined, color: props.onBrand || undefined }));

// which ready-made Custom widget this is, from its code when it is on a screen
const custom = computed(() => {
	if (props.preset) return props.preset;
	const code = String(props.settings.html || "");
	return code.includes('id="t"') ? "countdown" : code.includes('id="b"') ? "progress" : code.includes('id="m"') ? "rotating_messages" : "";
});

const align = computed(() => ({ start: "start", center: "center", end: "end" })[props.settings.align] || "start");
// the date in the workspace's own format, as a screen's clock shows one
const shown = date(today());
const dressed = computed(() => {
	const one = props.look || {};
	const line = one.borderStyle && one.borderStyle !== "none" ? Math.max(1, (Number(one.borderWidth) || 1) * props.scale) : 0;
	return {
		background: one.fillColor || undefined,
		// a screen's words are its brand's ink until a look says otherwise
		color: one.color || props.onBrand || undefined,
		fontFamily: one.fontFamily ? `'${one.fontFamily}'` : undefined,
		padding: one.padding ? `${one.padding * props.scale}px` : undefined,
		borderRadius: one.borderRadius ? `${Math.min(one.borderRadius * props.scale, 999)}px` : undefined,
		border: line ? `${line}px ${one.borderStyle} ${one.borderColor || "currentColor"}` : undefined,
		boxShadow: one.shadowColor && Number(one.shadowBlur) ? `0 ${2 * props.scale}px ${8 * props.scale}px ${one.shadowColor}` : undefined,
	};
});
</script>
