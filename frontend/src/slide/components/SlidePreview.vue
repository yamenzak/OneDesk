<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/SlidePreview.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div class="relative overflow-hidden" :style="previewStyles">
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
import { frame, frameSize } from '@/apps/slides/shim/frame.js' // One: the frame is one setting, a screen's may stand on its side (VENDORED.md)
import { computed } from 'vue'

import SlideElement from '@/apps/slides/components/SlideElement.vue'
import { underneath } from '@/apps/slides/shim/master.js' // One: the master, VENDORED.md
import { slides } from '@/apps/slides/stores/slide' // One

const props = defineProps({
	slide: { type: Object, required: true },
	scale: { type: Number, default: () => 160 / frame.w },
})

const own = computed(() => {
	const value = props.slide?.elements
	if (!value) return []
	if (Array.isArray(value)) return value

	try {
		return JSON.parse(value)
	} catch {
		return []
	}
})

// One: the master underneath, numbered by where the slide stands (VENDORED.md)
const elements = computed(() => {
	const index = slides.value.findIndex((one) => one === props.slide || (one.clientId && one.clientId === props.slide?.clientId))
	return [...underneath(props.slide, index), ...own.value]
})

const previewStyles = computed(() => ({
	background: props.slide?.background || '#ffffff', // One: a fade is a background too, VENDORED.md
	aspectRatio: `${frame.w} / ${frame.h}`, // One: the presentation's own shape, not 16:9 (VENDORED.md)
}))

const slideStyles = computed(() => ({
	...frameSize(),
	transformOrigin: 'top left',
	transform: `scale(${props.scale})`,
	position: 'absolute',
	top: '0',
	left: '0',
}))
</script>
