<!-- A widget on a screen's canvas (stage 7 of docs/ONESLIDE.md): its frame in its look, its name and where it reads from. What it shows is drawn by the screen itself, which Preview opens. One's own; VENDORED.md. -->
<template>
	<div class="relative size-full overflow-hidden" :style="dressed">
		<div class="absolute inset-0 flex flex-col items-center justify-center gap-1 rounded-4 border border-dashed border-outline-gray-4 px-2 text-center" :class="worn ? '' : 'bg-surface-gray-2'">
			<span class="max-w-full truncate font-medium" :class="[thin ? 'text-sm' : 'text-lg', worn ? '' : 'text-ink-gray-8']">{{ element.name || kind?.label || element.widget?.widget_type }}</span>
			<span v-if="!thin" class="max-w-full truncate text-sm opacity-70" :class="worn ? '' : 'text-ink-gray-5'">{{ said }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { screen } from "../stores/presentation";

const props = defineProps({ element: { type: Object, required: true } });
const kind = computed(() => (screen.value?.types || []).find((one) => one.type === props.element.widget?.widget_type));
const thin = computed(() => (props.element.height || 0) < 64);
const said = computed(() => [kind.value?.label, props.element.widget?.source].filter(Boolean).join(" · "));

// its look as the screen draws it (tv.js dress), so the canvas shows what plays
const worn = computed(() => Boolean(props.element.fillColor || props.element.color));
const dressed = computed(() => {
	const one = props.element;
	const line = one.borderStyle && one.borderStyle !== "none" ? Number(one.borderWidth) || 1 : 0;
	return {
		background: one.fillColor || undefined,
		color: one.color || undefined,
		fontFamily: one.fontFamily ? `'${one.fontFamily}'` : undefined,
		borderRadius: one.borderRadius ? `${one.borderRadius}px` : undefined,
		border: line ? `${line}px ${one.borderStyle} ${one.borderColor || "currentColor"}` : undefined,
	};
});
</script>
