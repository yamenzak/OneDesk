<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/BackgroundSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Background')">
		<PropertyRow :label="__('Fill')">
			<ColorPicker
				:modelValue="currentSlide.background"
				@update:modelValue="background.set"
				@colordown="background.begin"
				@colorup="background.commit"
			/>
		</PropertyRow>
	</Section>
</template>

<script setup>
import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { currentSlide } from '@/apps/slides/stores/slide'
import { useSlideProperty } from '@/apps/slides/composables/editProperty'

const background = useSlideProperty('background')
</script>
