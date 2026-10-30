<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/ParagraphSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Paragraph')">
		<PropertyRow :label="__('Align')">
			<TabButtons
				:modelValue="editorStyles.textAlign"
				:options="alignOptions"
				@update:modelValue="(value) => updateProperty('textAlign', value)"
			/>
		</PropertyRow>
		<PropertyRow v-if="showListStyle" :label="__('List Style')">
			<TabButtons
				:modelValue="listStyle"
				:options="listStyleOptions"
				@update:modelValue="(value) => updateProperty('list', value)"
			/>
		</PropertyRow>
		<NumberControl
			:modelValue="parseFloat(editorStyles.lineHeight) || 1.5"
			:label="__('Line Height')"
			:min="1"
			:max="5"
			:max-digits="3"
			:step="0.1"
			@update:modelValue="(value) => updateProperty('lineHeight', parseFloat(value))"
		/>
		<NumberControl
			:modelValue="editorStyles.letterSpacing || 0"
			:label="__('Letter Spacing')"
			suffix="px"
			:min="-10"
			:max="50"
			:max-digits="3"
			:step="1"
			@update:modelValue="(value) => updateProperty('letterSpacing', parseFloat(value))"
		/>
	</Section>
</template>

<script setup>
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { computed } from 'vue'

import { TabButtons } from 'frappe-ui'

import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import NumberControl from '@/apps/slides/components/controls/NumberControl.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { useTextEditor } from '@/apps/slides/composables/useTextEditor'
import { activeElement, activeElements, focusElementId } from '@/apps/slides/stores/element'

const { editorStyles, updateProperty } = useTextEditor()

const alignOptions = [
	{ value: 'left', tooltip: __('Align left'), icon: 'lucide-align-left' },
	{ value: 'center', tooltip: __('Align center'), icon: 'lucide-align-center' },
	{ value: 'right', tooltip: __('Align right'), icon: 'lucide-align-right' },
	{ value: 'justify', tooltip: __('Justify'), icon: 'lucide-align-justify' },
]

const listStyleOptions = [
	{ value: 'none', tooltip: __('None'), icon: 'lucide-ban' },
	{ value: 'bullet', tooltip: __('Bulleted'), icon: 'lucide-list' },
	{ value: 'ordered', tooltip: __('Numbered'), icon: 'lucide-list-ordered' },
]

const listStyle = computed(() =>
	editorStyles.orderedList ? 'ordered' : editorStyles.bulletList ? 'bullet' : 'none',
)

// a list wraps the block the caret is in, and a table selected as a whole has no caret
const showListStyle = computed(
	() =>
		activeElements.value.every((el) => el.type !== 'table') ||
		focusElementId.value === activeElement.value?.id,
)
</script>
