<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/ShadowSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Shadow')" :initialState="hasShadow">
		<PropertyRow :label="__('Color')">
			<ColorPicker
				:modelValue="firstEditableElement.shadowColor ?? defaultShadowColor"
				@update:modelValue="shadowColor.set"
				@colordown="shadowColor.begin"
				@colorup="shadowColor.commit"
			/>
		</PropertyRow>
		<NumberControl
			:modelValue="firstEditableElement.shadowBlur ?? 0"
			:label="__('Blur')"
			suffix="%"
			:min="0"
			:max="100"
			:max-digits="3"
			:step="1"
			@update:modelValue="shadowBlur.set"
			@change-start="shadowBlur.begin"
			@change-end="shadowBlur.commit"
		/>
		<NumberControl
			:modelValue="firstEditableElement.shadowOpacity ?? 100"
			:label="__('Opacity')"
			suffix="%"
			:min="0"
			:max="100"
			:max-digits="3"
			:step="1"
			@update:modelValue="shadowOpacity.set"
			@change-start="shadowOpacity.begin"
			@change-end="shadowOpacity.commit"
		/>
		<NumberControl
			:modelValue="firstEditableElement.shadowOffset ?? 0"
			:label="__('Offset')"
			suffix="%"
			:min="0"
			:max="100"
			:max-digits="3"
			:step="1"
			@update:modelValue="shadowOffset.set"
			@change-start="shadowOffset.begin"
			@change-end="shadowOffset.commit"
		/>
		<NumberControl
			:modelValue="firstEditableElement.shadowAngle ?? 45"
			:label="__('Angle')"
			suffix="°"
			:min="0"
			:max="360"
			:max-digits="3"
			:step="1"
			@update:modelValue="shadowAngle.set"
			@change-start="shadowAngle.begin"
			@change-end="shadowAngle.commit"
		/>
	</Section>
</template>

<script setup>
import { computed } from 'vue'

import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import NumberControl from '@/apps/slides/components/controls/NumberControl.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { firstEditableElement } from '@/apps/slides/stores/element'
import { useElementProperty } from '@/apps/slides/composables/editProperty'
import { defaultShadowColor } from '@/apps/slides/utils/constants'

const defaultShadowBlur = 10

const hasShadow = computed(() =>
	Boolean(firstEditableElement.value.shadowBlur || firstEditableElement.value.shadowOffset),
)

const useShadowProperty = (property) => {
	const elementProperty = useElementProperty(property)

	const setWithShadow = (el, value) => {
		el[property] = value
		if (!el.shadowBlur && !el.shadowOffset) el.shadowBlur = defaultShadowBlur
	}

	return {
		...elementProperty,
		set: (value) => elementProperty.setEach((el) => setWithShadow(el, value)),
		begin: () => elementProperty.begin([property, 'shadowBlur']),
	}
}

const shadowColor = useShadowProperty('shadowColor')
const shadowOpacity = useShadowProperty('shadowOpacity')
const shadowAngle = useShadowProperty('shadowAngle')
const shadowBlur = useElementProperty('shadowBlur')
const shadowOffset = useElementProperty('shadowOffset')
</script>
