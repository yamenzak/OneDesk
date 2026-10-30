<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/ThumbnailCapture.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div
		ref="captureRef"
		class="pointer-events-none fixed left-[-10000px] top-0 overflow-hidden"
		:style="frameSize()"
	>
		<div class="overflow-hidden" :style="frameSize()">
			<SlidePreview v-if="slide" :slide="slide" :scale="1" />
		</div>
	</div>
</template>

<script setup>
import { frameSize } from '@/apps/slides/shim/frame.js' // One: the frame is one setting, a screen's may stand on its side (VENDORED.md)
import { toRef, useTemplateRef } from 'vue'

import SlidePreview from '@/apps/slides/components/SlidePreview.vue'

import { useThumbnailCapture } from '@/apps/slides/composables/useThumbnailCapture'

const props = defineProps({
	slide: {
		type: Object,
		default: null,
	},
	disableCapture: {
		type: Boolean,
		default: false,
	},
})

const captureRef = useTemplateRef('captureRef')

const thumbnailCaptureControls = useThumbnailCapture(captureRef, toRef(props, 'disableCapture'))

defineExpose(thumbnailCaptureControls)
</script>
