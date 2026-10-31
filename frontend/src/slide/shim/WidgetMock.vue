<!-- A widget drawn small, in its look, for Add a Widget and the canvas:
     what it will show, with example words, sized in em from its own box as
     the screen sizes it (one_display/widgets.py PRESETS). One's own;
     VENDORED.md. -->
<template>
	<div class="flex size-full flex-col items-center justify-center overflow-hidden text-center leading-tight" :style="dressed">
		<template v-if="type === 'Clock' && layout === 'analog'">
			<svg viewBox="0 0 100 100" class="size-full" :style="{ maxWidth: '100%', maxHeight: '100%' }">
				<line v-for="i in 60" :key="i" x1="50" :y1="i % 5 ? 5 : 4" x2="50" :y2="i % 5 ? 7.5 : 11" stroke="currentColor" :stroke-width="i % 5 ? 0.8 : 2.2" stroke-linecap="round" :opacity="i % 5 ? 0.45 : 1" :transform="`rotate(${i * 6} 50 50)`" />
				<line x1="50" y1="54" x2="50" y2="27" stroke="currentColor" stroke-width="4.4" stroke-linecap="round" transform="rotate(290 50 50)" />
				<line x1="50" y1="56" x2="50" y2="15" stroke="currentColor" stroke-width="3" stroke-linecap="round" transform="rotate(246 50 50)" />
				<line x1="50" y1="60" x2="50" y2="12" :stroke="brand" stroke-width="1.2" stroke-linecap="round" transform="rotate(130 50 50)" />
				<circle cx="50" cy="50" r="2.6" fill="currentColor" />
			</svg>
		</template>
		<template v-else-if="type === 'Clock' && layout === 'date'">
			<span class="font-semibold uppercase opacity-75" :style="{ ...em(0.8), letterSpacing: '0.12em' }">{{ weekday }}</span>
			<span class="font-bold leading-none" :style="em(3.6)">{{ dayOfMonth }}</span>
			<span class="opacity-75" :style="em(0.9)">{{ month }}</span>
		</template>
		<div v-else-if="type === 'Clock' && layout === 'stacked'" class="flex w-full flex-col items-start text-start" :style="{ padding: '0 0.4em' }">
			<span class="font-semibold leading-none tabular-nums" :style="em(2.6)">09:41</span>
			<span class="font-semibold" :style="{ ...em(1), marginTop: '0.35em' }">{{ weekday }}</span>
			<span class="opacity-75" :style="em(0.9)">{{ dayOfMonth }} {{ month }}</span>
		</div>
		<span v-else-if="type === 'Clock' && layout === 'minimal'" class="font-extralight leading-none tabular-nums" :style="em(3.4)">09:41</span>
		<template v-else-if="type === 'Clock'">
			<span class="font-semibold tabular-nums" :style="em(2.6)">{{ settings.hours === "12" ? "9:41" : "09:41" }}</span>
			<span v-if="settings.date !== 0" class="opacity-80" :style="em(0.8)">{{ shown }}</span>
		</template>
		<span v-else-if="type === 'Text'" class="w-full font-semibold" :style="{ fontSize: frameHigh ? `${((settings.size || 5) / 100) * frameHigh}px` : `${settings.size || 5}cqh`, textAlign: align, padding: '0 0.3em' }">{{ settings.text || __("Text") }}</span>
		<span v-else-if="type === 'Ticker' && layout === 'fade'" class="w-full truncate font-semibold" :style="em(2.2)">{{ settings.text || __("Welcome") }}</span>
		<div v-else-if="type === 'Ticker' && layout === 'labelled'" class="flex size-full items-stretch">
			<span class="flex items-center font-bold uppercase" :style="{ ...chip, ...em(1.6), padding: '0 0.6em', letterSpacing: '0.08em' }">{{ settings.label || __("News") }}</span>
			<span class="flex items-center truncate whitespace-nowrap" :style="{ ...em(2.2), padding: '0 0.4em' }">{{ [__("Latest news"), __("Opening hours")].join("\u2003•\u2003") }}</span>
		</div>
		<div v-else-if="type === 'Ticker'" class="w-full truncate whitespace-nowrap text-start" :style="{ ...em(2.6), padding: '0 0.3em' }">{{ [__("Latest news"), __("Opening hours"), __("Welcome")].join("\u2003•\u2003") }}</div>
		<template v-else-if="type === 'Queue Board' && layout === 'latest'">
			<span class="uppercase opacity-70" :style="em(0.7)">{{ settings.heading || __("Now Serving") }}</span>
			<span class="font-bold leading-none" :style="em(3)">A012</span>
			<span class="opacity-80" :style="{ ...em(0.9), marginTop: '0.3em' }">{{ __("Counter {0}", [2]) }}</span>
		</template>
		<div v-else-if="type === 'Queue Board' && layout === 'counters'" class="grid size-full grid-cols-2" :style="{ gap: '0.3em', padding: '0.3em' }">
			<div v-for="(one, at) in ['A012', 'B007', 'A011', 'C004']" :key="one" class="flex flex-col items-center justify-center" :style="{ borderRadius: '0.3em', background: at === 0 ? brand : 'color-mix(in srgb, currentColor 14%, transparent)', color: at === 0 ? onBrand || undefined : undefined }">
				<span class="uppercase opacity-70" :style="em(0.55)">{{ __("Counter {0}", [at + 1]) }}</span>
				<span class="font-bold" :style="em(1.3)">{{ one }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Queue Board' && layout === 'list'" class="flex w-full flex-col text-start" :style="{ padding: '0.4em' }">
			<div v-for="(one, at) in ['A012', 'B007', 'A011', 'C004']" :key="one" class="flex items-center whitespace-nowrap" :style="{ ...em(at ? 0.9 : 1.15), padding: '0.25em 0', borderBottom: '0.04em solid color-mix(in srgb, currentColor 30%, transparent)' }">
				<span class="font-bold" :style="{ minWidth: '3.4em', color: at ? undefined : brand }">{{ one }}</span><span class="opacity-40">→</span><span class="ms-auto opacity-80">{{ __("Counter {0}", [(at % 3) + 1]) }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Queue Board' && layout === 'waiting'" class="flex w-full flex-col text-start" :style="{ padding: '0.4em' }">
			<span class="uppercase opacity-70" :style="em(0.7)">{{ __("Waiting") }}</span>
			<div v-for="(one, at) in [[__('Enquiries'), 4], [__('Payments'), 2], [__('Collections'), 7]]" :key="at" class="flex items-center" :style="{ padding: '0.25em 0' }">
				<span class="font-bold" :style="{ ...em(0.8), background: 'color-mix(in srgb, currentColor 18%, transparent)', borderRadius: '0.25em', padding: '0 0.35em', marginInlineEnd: '0.5em' }">{{ "ABC"[at] }}</span>
				<span class="flex-1 truncate font-semibold" :style="em(0.9)">{{ one[0] }}</span><span class="font-bold" :style="em(1.4)">{{ one[1] }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Queue Board'" class="flex w-full flex-col text-start" :style="{ gap: '0.3em', padding: '0.4em' }">
			<span class="uppercase opacity-70" :style="em(0.7)">{{ settings.heading || __("Now Serving") }}</span>
			<div class="flex items-baseline justify-between" :style="{ ...chip, borderRadius: '0.3em', padding: '0.2em 0.5em' }">
				<span class="font-bold" :style="em(1.6)">A012</span><span class="whitespace-nowrap" :style="em(0.8)">{{ __("Counter {0}", [2]) }}</span>
			</div>
			<div v-for="one in ['B007', 'A011']" :key="one" class="flex justify-between whitespace-nowrap" :style="em(0.9)"><span class="font-semibold">{{ one }}</span><span class="opacity-70">{{ __("Counter {0}", [1]) }}</span></div>
		</div>
		<div v-else-if="type === 'Kiosk' && layout === 'list'" class="flex w-full flex-col" :style="{ gap: '0.3em', padding: '0.5em' }">
			<span class="font-semibold" :style="{ ...em(1.1), marginBottom: '0.2em' }">{{ settings.heading || __("Take a ticket") }}</span>
			<div v-for="(one, at) in services" :key="at" class="flex items-center text-start" :style="{ ...em(0.75), padding: '0.35em 0.5em', borderRadius: '0.35em', background: 'color-mix(in srgb, currentColor 12%, transparent)' }">
				<span class="font-bold" :style="{ ...chip, ...square(1.6), lineHeight: '1.6em', textAlign: 'center', borderRadius: '0.3em', marginInlineEnd: '0.6em' }">{{ one[0] }}</span>
				<span class="flex-1 truncate font-semibold">{{ one[1] }}</span>
				<span class="whitespace-nowrap opacity-60" :style="em(0.75)">{{ __("{0} waiting", [one[2]]) }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Kiosk'" class="flex size-full flex-col" :style="{ gap: '0.4em', padding: '0.5em' }">
			<span class="font-semibold" :style="em(1.1)">{{ settings.heading || __("Take a ticket") }}</span>
			<div class="grid flex-1 grid-cols-3" :style="{ gap: '0.3em' }">
				<span v-for="(one, at) in services" :key="at" class="flex flex-col justify-between text-start" :style="{ ...chip, borderRadius: '0.4em', padding: '0.4em 0.5em' }">
					<span class="font-bold leading-none" :style="em(1.6)">{{ one[0] }}</span>
					<span class="font-semibold" :style="em(0.7)">{{ one[1] }}</span>
				</span>
			</div>
		</div>
		<div v-else-if="type === 'Weather' && layout === 'today'" class="flex items-center" :style="{ gap: '0.5em' }">
			<Icon icon="lucide-sun" :style="square(3)" />
			<div class="flex flex-col text-start">
				<span class="font-light leading-none" :style="em(2.4)">24°</span>
				<span class="font-semibold" :style="em(0.9)">{{ __("Clear sky") }}</span>
				<span class="flex opacity-75" :style="{ ...em(0.75), gap: '0.6em' }"><span>↑ 31°</span><span>↓ 23°</span></span>
			</div>
		</div>
		<div v-else-if="type === 'Weather' && layout === 'hours'" class="flex w-full flex-col" :style="{ padding: '0 0.3em' }">
			<span class="text-start opacity-80" :style="em(0.75)">24° {{ __("Clear sky") }}</span>
			<div class="flex w-full justify-between" :style="{ marginTop: '0.4em' }">
				<div v-for="(one, at) in hourRow" :key="at" class="flex flex-col items-center">
					<span class="opacity-70" :style="em(0.65)">{{ one[0] }}</span>
					<Icon :icon="one[1]" :style="{ ...square(1.3), margin: '0.2em 0' }" />
					<span class="font-semibold" :style="em(0.85)">{{ one[2] }}</span>
				</div>
			</div>
		</div>
		<div v-else-if="type === 'Weather' && layout === 'list'" class="flex size-full flex-col justify-around" :style="{ padding: '0.3em 0.5em' }">
			<div v-for="(one, at) in weekRows" :key="at" class="flex items-center" :style="em(0.8)">
				<span class="font-semibold" :style="{ width: '3.6em' }">{{ one[0] }}</span>
				<span class="opacity-60" :style="{ width: '1.8em' }">{{ one[1] }}°</span>
				<span class="relative flex-1 rounded-full" :style="{ height: '0.3em', margin: '0 0.5em', background: 'color-mix(in srgb, currentColor 25%, transparent)' }"><i class="absolute top-0 h-full rounded-full" :style="{ left: `${one[3]}%`, width: `${one[4]}%`, background: 'currentColor' }" /></span>
				<span class="font-semibold" :style="{ width: '1.8em' }">{{ one[2] }}°</span>
			</div>
		</div>
		<span v-else-if="type === 'Weather' && layout === 'compact'" class="flex items-center whitespace-nowrap font-semibold" :style="{ ...em(2), gap: '0.25em' }"><Icon icon="lucide-sun" :style="square(1.1)" />24°</span>
		<template v-else-if="type === 'Weather' && layout === 'big'">
			<Icon icon="lucide-sun" :style="square(1.8)" />
			<span class="font-extralight leading-none" :style="em(3.8)">24°</span>
			<span class="opacity-75" :style="em(0.8)">{{ __("Clear sky") }}</span>
		</template>
		<div v-else-if="type === 'Weather'" class="flex w-full flex-col" :style="{ padding: '0 0.4em' }">
			<div class="flex items-center" :style="{ gap: '0.4em' }">
				<Icon icon="lucide-sun" :style="square(1.8)" />
				<div class="flex flex-col text-start">
					<span class="font-semibold leading-none" :style="em(1.8)">24°</span>
					<span class="opacity-80" :style="em(0.7)">{{ __("Clear sky") }}</span>
				</div>
			</div>
			<div v-if="settings.days !== 0" class="flex w-full justify-around" :style="{ marginTop: '0.5em' }">
				<div v-for="(one, at) in weekRows.slice(1, 1 + Math.min(settings.days ?? 3, 3))" :key="at" class="flex flex-col items-center">
					<span class="opacity-75" :style="em(0.6)">{{ one[0] }}</span>
					<Icon :icon="one[5]" :style="{ ...square(1), margin: '0.2em 0' }" />
					<span class="font-semibold" :style="em(0.75)">{{ one[2] }}°</span>
					<span class="opacity-60" :style="em(0.65)">{{ one[1] }}°</span>
				</div>
			</div>
		</div>
		<div v-else-if="type === 'Board' && layout === 'list'" class="flex w-full flex-col text-start" :style="{ padding: '0.3em 0.5em' }">
			<div v-for="(one, at) in boardRows" :key="at" class="flex items-center" :style="{ ...em(0.85), padding: '0.22em 0', borderBottom: '0.04em solid color-mix(in srgb, currentColor 25%, transparent)' }">
				<span class="rounded-full" :style="{ width: '0.7em', height: '0.7em', marginInlineEnd: '0.6em', background: brand, opacity: one[2] }" />
				<span class="flex-1 truncate font-semibold">{{ one[0] }}</span><span class="opacity-80">{{ one[1] }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Board' && layout === 'summary'" class="flex size-full items-center justify-around">
			<div v-for="(one, at) in [[6, __('Free'), 1], [3, __('In Use'), 0.6], [1, __('Cleaning'), 0.35]]" :key="at" class="flex flex-col items-center">
				<span class="font-bold leading-none" :style="{ ...em(2.6), color: brand, opacity: one[2] }">{{ one[0] }}</span>
				<span class="opacity-80" :style="em(0.8)">{{ one[1] }}</span>
			</div>
		</div>
		<div v-else-if="type === 'Board'" class="grid size-full" :style="{ gap: '0.3em', padding: '0.4em', gridTemplateColumns: `repeat(${settings.columns || 3}, minmax(0, 1fr))` }">
			<span v-for="one in (settings.columns || 3) * 2" :key="one" class="flex items-end" :style="{ ...chip, ...em(0.6), borderRadius: '0.3em', padding: '0.2em', opacity: [1, 0.55, 0.8, 0.4, 0.9, 0.65, 1, 0.5][one % 8] }">{{ one }}</span>
		</div>
		<template v-else-if="type === 'Board Item'">
			<span class="font-semibold" :style="em(1.4)">{{ __("Room {0}", [1]) }}</span>
			<span class="rounded-full" :style="{ ...chip, ...em(0.8), marginTop: '0.3em', padding: '0 0.6em' }">{{ __("Free") }}</span>
		</template>
		<img v-else-if="type === 'Image' && settings.image" :src="settings.image" alt="" class="size-full" :class="settings.fit === 'cover' ? 'object-cover' : 'object-contain'" />
		<Icon v-else-if="type === 'Image'" icon="lucide-image" class="opacity-70" :style="square(2.4)" />
		<div v-else-if="type === 'QR Code' && layout === 'side'" class="flex size-full items-center" :style="{ gap: '0.6em', padding: '0 0.4em' }">
			<Icon icon="lucide-qr-code" :style="square(2.6)" />
			<span class="text-start font-semibold leading-tight" :style="em(0.9)">{{ settings.caption }}</span>
		</div>
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
import { date, dayWords, today } from "../../kit/desk";
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
const layout = computed(() => props.settings.layout || "");

// example words in the reader's language, as the screen gets them from the server
const weekday = dayWords(0, "dddd");
const month = dayWords(0, "MMMM YYYY");
const dayOfMonth = dayWords(0, "D");
const hourRow = [[__("Now"), "lucide-sun", "24°"], ["15:00", "lucide-sun", "26°"], ["16:00", "lucide-cloud-sun", "25°"], ["17:00", "lucide-cloud-sun", "23°"], ["18:00", "lucide-cloud", "21°"], ["19:00", "lucide-moon", "20°"]];
const nextDay = (days) => dayWords(days, "ddd");
const weekRows = [[__("Today"), 23, 31, 20, 60, "lucide-sun"], [nextDay(1), 24, 32, 30, 62, "lucide-cloud-sun"], [nextDay(2), 22, 29, 10, 55, "lucide-sun"], [nextDay(3), 21, 28, 0, 58, "lucide-cloud"]];
const services = [["A", __("Enquiries"), 4], ["B", __("Payments"), 2], ["C", __("Collections"), 7]];
const boardRows = [[__("Room {0}", [1]), __("Free"), 1], [__("Room {0}", [2]), __("In Use"), 0.55], [__("Room {0}", [3]), __("Cleaning"), 0.35], [__("Room {0}", [4]), __("Free"), 1]];
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
