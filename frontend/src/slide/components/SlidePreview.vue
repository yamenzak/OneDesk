<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/SlidePreview.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div class="relative aspect-video overflow-hidden" :style="previewStyles">
		<div :style="slideStyles">
			<SlideElement
				v-for="element in elements"
				:key="`thumbnail-${element.id}`"
				mode="thumbnail"
				:element="element"
				:data-index="element.id"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import SlideElement from '@/apps/slides/components/SlideElement.vue'

const props = defineProps({
	slide: { type: Object, required: true },
	scale: { type: Number, default: 160 / 960 },
})

const elements = computed(() => {
	const value = props.slide?.elements
	if (!value) return []
	if (Array.isArray(value)) return value

	try {
		return JSON.parse(value)
	} catch {
		return []
	}
})

const previewStyles = computed(() => ({
	background: props.slide?.background || '#ffffff', // One: a fade is a background too, VENDORED.md
}))

const slideStyles = computed(() => ({
	width: '960px',
	height: '540px',
	transformOrigin: 'top left',
	transform: `scale(${props.scale})`,
	position: 'absolute',
	top: '0',
	left: '0',
}))
</script>
