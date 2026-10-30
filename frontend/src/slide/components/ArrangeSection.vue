<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/ArrangeSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Arrange')">
		<ButtonGroup :label="__('Order')" :options="orderOptions" @select="arrangeElements" />
		<ButtonGroup
			:label="__('Align Horizontal')"
			:options="alignHorizontalOptions"
			:active="alignedDirections"
			@select="alignElement"
			@hover="onAlignHover"
		/>
		<ButtonGroup
			:label="__('Align Vertical')"
			:options="alignVerticalOptions"
			:active="alignedDirections"
			@select="alignElement"
			@hover="onAlignHover"
		/>
		<ButtonGroup
			v-if="!isOnlyLines"
			:label="__('Flip')"
			:options="flipOptions"
			@select="flipElements"
		/>
	</Section>
</template>

<script setup>
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { computed } from 'vue'

import ButtonGroup from '@/apps/slides/components/controls/ButtonGroup.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import BringToFront from '@/apps/slides/icons/BringToFront.vue'
import SendToBack from '@/apps/slides/icons/SendToBack.vue'
import Forward from '@/apps/slides/icons/Forward.vue'
import Backward from '@/apps/slides/icons/Backward.vue'

import AlignLeft from '@/apps/slides/icons/AlignLeft.vue'
import AlignCenter from '@/apps/slides/icons/AlignCenter.vue'
import AlignRight from '@/apps/slides/icons/AlignRight.vue'
import AlignTop from '@/apps/slides/icons/AlignTop.vue'
import AlignCenterVertical from '@/apps/slides/icons/AlignCenterVertical.vue'
import AlignBottom from '@/apps/slides/icons/AlignBottom.vue'

import FlipHorizontal from '@/apps/slides/icons/FlipHorizontal.vue'
import FlipVertical from '@/apps/slides/icons/FlipVertical.vue'

import { guideVisibilityMap } from '@/apps/slides/stores/slide'
import { activeElementIds, activeElements, flipElements } from '@/apps/slides/stores/element'
import {
	alignElement,
	arrangeElements,
	getAlignedDirections,
} from '@/apps/slides/stores/placement'

const orderOptions = [
	{ value: 'front', label: __('Bring to front'), icon: BringToFront },
	{ value: 'back', label: __('Send to back'), icon: SendToBack },
	{ value: 'forward', label: __('Bring forward'), icon: Forward },
	{ value: 'backward', label: __('Send backward'), icon: Backward },
]

const alignHorizontalOptions = [
	{ value: 'left', label: __('Align left'), icon: AlignLeft },
	{ value: 'horizontalCenter', label: __('Align center'), icon: AlignCenter },
	{ value: 'right', label: __('Align right'), icon: AlignRight },
]

const alignVerticalOptions = [
	{ value: 'top', label: __('Align top'), icon: AlignTop },
	{ value: 'verticalCenter', label: __('Align middle'), icon: AlignCenterVertical },
	{ value: 'bottom', label: __('Align bottom'), icon: AlignBottom },
]

// mirroring a line only swaps its heads around; nothing else is visible
const isOnlyLines = computed(() => activeElements.value.every((el) => el.shapeType === 'line'))

const flipOptions = [
	{ value: 'horizontal', label: __('Flip horizontal'), icon: FlipHorizontal },
	{ value: 'vertical', label: __('Flip vertical'), icon: FlipVertical },
]

const alignedDirections = computed(() => getAlignedDirections())

const alignGuideMap = {
	left: 'leftEdge',
	horizontalCenter: 'centerY',
	right: 'rightEdge',
	top: 'topEdge',
	verticalCenter: 'centerX',
	bottom: 'bottomEdge',
}

const onAlignHover = (direction) => {
	for (const key in guideVisibilityMap) guideVisibilityMap[key] = false
	if (!direction || activeElementIds.value.length > 1) return
	guideVisibilityMap[alignGuideMap[direction]] = true
}
</script>
