<!-- A widget on a screen's canvas (stage 7 of docs/ONESLIDE.md): its frame, its name and where it reads from. What it shows is drawn by the screen itself, which Preview opens. One's own; VENDORED.md. -->
<template>
	<div class="flex size-full flex-col items-center justify-center gap-1 overflow-hidden rounded-4 border border-dashed border-outline-gray-4 bg-surface-gray-2 px-2 text-center">
		<span class="max-w-full truncate font-medium text-ink-gray-8" :class="thin ? 'text-sm' : 'text-lg'">{{ element.name || kind?.label || element.widget?.widget_type }}</span>
		<span v-if="!thin" class="max-w-full truncate text-sm text-ink-gray-5">{{ said }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { screen } from "../stores/presentation";

const props = defineProps({ element: { type: Object, required: true } });
const kind = computed(() => (screen.value?.types || []).find((one) => one.type === props.element.widget?.widget_type));
const thin = computed(() => (props.element.height || 0) < 64);
const said = computed(() => [kind.value?.label, props.element.widget?.source].filter(Boolean).join(" · "));
</script>
