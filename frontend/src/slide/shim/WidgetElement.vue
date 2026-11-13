<!-- A widget on a screen's canvas (stage 7 of docs/ONEDECK.md): drawn as it
     will look, in its look, with example words where its rows will be, and
     its kind and source named underneath. Preview plays the real thing.
     One's own; VENDORED.md. -->
<template>
	<div class="relative size-full overflow-hidden" :style="{ fontSize: `${Math.max((element.height || 0) / 6, 6)}px` }">
		<WidgetMock :type="element.widget?.widget_type || ''" :settings="settings" :look="look" :brand="screen?.brand || ''" :on-brand="onBrand" :frame-high="frame.h" />
		<span v-if="!thin" class="absolute bottom-1 start-1 max-w-[90%] truncate rounded-4 bg-surface-base/80 px-1.5 text-xs leading-5 text-ink-gray-6">{{ said }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { screen } from "../stores/presentation";
import { frame } from "./frame.js";
import WidgetMock from "./WidgetMock.vue";

const props = defineProps({ element: { type: Object, required: true } });
// the words on the business's colour, as its Accent look has them
const onBrand = computed(() => (screen.value?.looks || []).find((one) => one.name === "Accent")?.look.color || "");
const kind = computed(() => (screen.value?.types || []).find((one) => one.type === props.element.widget?.widget_type));
const thin = computed(() => (props.element.height || 0) < 64);
const said = computed(() => [props.element.name || kind.value?.label, props.element.widget?.source].filter(Boolean).join(" · "));

// the widget's settings as saved, a JSON string when it came from the server
const settings = computed(() => {
	const kept = props.element.widget?.settings;
	if (kept && typeof kept === "object") return kept;
	try {
		return JSON.parse(kept || "{}") || {};
	} catch {
		return {};
	}
});

// its look is the element's own, as the screen draws it (tv.js dress)
const KEYS = ["fillColor", "color", "accentColor", "fontFamily", "padding", "textSize", "mainSize", "labelSize", "detailSize", "borderStyle", "borderColor", "borderWidth", "borderRadius", "shadowColor", "shadowBlur", "shadowOpacity", "shadowOffset", "shadowAngle"];
const look = computed(() => Object.fromEntries(KEYS.filter((key) => props.element[key] != null && props.element[key] !== "").map((key) => [key, props.element[key]])));
</script>
