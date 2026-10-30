<!-- Blur and a free CSS box for whatever is selected: the Builder half of the panel. One's own; VENDORED.md. -->
<template>
	<Section :label="__('Effects')">
		<NumberControl
			:modelValue="firstEditableElement.blur ?? 0"
			:label="__('Blur')"
			suffix="px"
			:min="0"
			:max="rules.mostBlur"
			:max-digits="3"
			@update:modelValue="(value) => blur.set(Number(value) || 0)"
			@change-start="blur.begin"
			@change-end="blur.commit"
		/>
		<div class="flex flex-col gap-1.5">
			<span :class="labelClasses">{{ __('CSS') }}</span>
			<textarea
				:value="draft"
				rows="4"
				spellcheck="false"
				dir="ltr"
				:placeholder="__('For example: border-radius: 24px; mix-blend-mode: multiply')"
				class="w-full resize-y rounded-4 border-0 bg-surface-gray-2 px-2 py-1.5 font-mono text-xs text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-1 focus:ring-outline-gray-3"
				@input="draft = $event.target.value"
				@blur="keep"
				@keydown.stop
			/>
			<span v-if="dropped.length" class="text-xs text-ink-red-4">
				{{ __("Not used: {0}", [dropped.join(", ")]) }}
			</span>
		</div>
	</Section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import NumberControl from '../components/controls/NumberControl.vue'
import Section from '../components/controls/Section.vue'
import { useElementProperty, setElementProperty } from '../composables/editProperty'
import { firstEditableElement } from '../stores/element'
import { labelClasses } from '../utils/constants'
import rules from '../../../../onedesk/one_slide/css.json'
import { readCss } from './looks.js'
import { __ } from './words.js'

const blur = useElementProperty('blur')

const draft = ref('')
watch(
	() => [firstEditableElement.value?.id, firstEditableElement.value?.css],
	() => (draft.value = firstEditableElement.value?.css || ''),
	{ immediate: true },
)

const dropped = computed(() => readCss(draft.value).dropped)

const keep = () => {
	const css = draft.value.trim()
	if (css !== (firstEditableElement.value?.css || '')) setElementProperty('css', css || undefined)
}
</script>
