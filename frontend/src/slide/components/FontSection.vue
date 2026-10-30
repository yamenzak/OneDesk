<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/FontSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Font')">
		<PropertyRow :label="__('Family')">
			<Combobox
				trigger="button"
				variant="ghost"
				size="sm"
				align="end"
				:options="textFonts"
				:modelValue="displayFont"
				class="-me-1"
				@update:modelValue="(value) => updateProperty('fontFamily', value)"
			/>
		</PropertyRow>
		<NumberControl
			:modelValue="editorStyles.fontSize"
			:label="__('Size')"
			suffix="px"
			:min="5"
			:max="800"
			:max-digits="3"
			:step="1"
			@update:modelValue="(value) => updateProperty('fontSize', value)"
		/>
		<PropertyRow :label="__('Color')">
			<ColorPicker
				:modelValue="editorStyles.color"
				@update:modelValue="(value) => updateProperty('color', value)"
			/>
		</PropertyRow>
		<ToggleGroup
			:label="__('Style')"
			:modelValue="decorValues"
			:options="decorOptions"
			@update:modelValue="onDecorToggle"
		/>
		<PropertyRow :label="__('Case')">
			<TabButtons
				:modelValue="editorStyles.textTransform"
				:options="caseOptions"
				@update:modelValue="(value) => updateProperty('textTransform', value)"
			/>
		</PropertyRow>
	</Section>
</template>

<script setup>
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { computed } from 'vue'

import { Combobox, TabButtons } from 'frappe-ui'
import { Bold, Italic, Underline, Strikethrough } from 'lucide-vue-next'

import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import NumberControl from '@/apps/slides/components/controls/NumberControl.vue'
import ToggleGroup from '@/apps/slides/components/controls/ToggleGroup.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { useTextEditor } from '@/apps/slides/composables/useTextEditor'

const { editorStyles, updateProperty, toggleMark } = useTextEditor()

const textFonts = [
	'Anton',
	'Arial',
	'Arial Black',
	'Comic Sans MS',
	'Courier New',
	'Courier Prime',
	'Georgia',
	'Helvetica',
	'Impact',
	'Lucida Console',
	'Lucida Sans Unicode',
	'Palatino Linotype',
	'Tahoma',
	'Times New Roman',
	'Trebuchet MS',
	'Verdana',
	'Inter',
]

const decorOptions = [
	{ value: 'bold', label: __('Bold'), icon: Bold },
	{ value: 'italic', label: __('Italic'), icon: Italic },
	{ value: 'underline', label: __('Underline'), icon: Underline },
	{ value: 'strike', label: __('Strikethrough'), icon: Strikethrough },
]

const caseOptions = [
	{ value: 'none', tooltip: __('As typed'), icon: 'lucide-ban' },
	{ value: 'uppercase', tooltip: __('Uppercase'), icon: 'lucide-case-upper' },
	{ value: 'lowercase', tooltip: __('Lowercase'), icon: 'lucide-case-lower' },
]

const displayFont = computed(() => editorStyles.fontFamily?.replace(/['"]/g, ''))

const decorValues = computed(() =>
	decorOptions.filter((option) => editorStyles[option.value]).map((option) => option.value),
)

const onDecorToggle = (values) => {
	const changed = decorOptions.find(
		(option) => decorValues.value.includes(option.value) !== values.includes(option.value),
	)
	if (changed) toggleMark(changed.value)
}
</script>
