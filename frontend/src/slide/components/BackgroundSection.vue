<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/BackgroundSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Background')">
		<PropertyRow :label="__('Fill')">
			<ColorPicker
				:modelValue="fade?.from || currentSlide.background"
				@update:modelValue="(from) => background.set(fade ? fadeText({ ...fade, from }) : from)"
				@colordown="background.begin"
				@colorup="background.commit"
			/>
		</PropertyRow>
		<!-- One: a background may fade into a second colour, shim/FadeRows.vue; VENDORED.md -->
		<FadeRows
			:fade="fade"
			:from="fade?.from || currentSlide.background"
			@toggle="toggleFade"
			@begin="background.begin"
			@set="(value) => background.set(fadeText({ ...value, from: fade.from }))"
			@commit="background.commit"
		/>
	</Section>
</template>

<script setup>
import { computed } from 'vue'

import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import Section from '@/apps/slides/components/controls/Section.vue'
import FadeRows from '@/apps/slides/shim/FadeRows.vue'

import { currentSlide } from '@/apps/slides/stores/slide'
import { useSlideProperty } from '@/apps/slides/composables/editProperty'
import { fadeOf, fadeText } from '@/apps/slides/shim/looks.js'

const background = useSlideProperty('background')

const fade = computed(() => fadeOf(currentSlide.value.background))

const toggleFade = (value) => {
	const from = fade.value?.from || currentSlide.value.background || '#ffffffff'
	background.begin()
	background.set(value ? fadeText({ ...value, from }) : from)
	background.commit()
}
</script>
