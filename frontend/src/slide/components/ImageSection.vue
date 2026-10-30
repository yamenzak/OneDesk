<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/ImageSection.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Section :label="__('Image')">
		<PropertyRow :label="__('Replace')">
			<Button variant="ghost" class="max-w-[45%]" :tooltip="fileName" @click="openFilePicker">
				<span class="min-w-0 truncate text-ink-gray-7">{{ fileName }}</span>
			</Button>
		</PropertyRow>
		<ButtonGroup :label="__('Crop')" :options="cropOptions" @select="handleCropAction" />
		<input
			ref="filePicker"
			type="file"
			class="hidden"
			:accept="allowedImageFileTypes.join(',')"
			@change="replaceImage"
		/>
	</Section>
</template>

<script setup>
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { computed, useTemplateRef } from 'vue'

import { Button } from 'frappe-ui'

import LucideCrop from '~icons/lucide/crop'
import LucideRotateCcw from '~icons/lucide/rotate-ccw'

import ButtonGroup from '@/apps/slides/components/controls/ButtonGroup.vue'
import PropertyRow from '@/apps/slides/components/controls/PropertyRow.vue'
import Section from '@/apps/slides/components/controls/Section.vue'

import { activeElement, activeElementIds } from '@/apps/slides/stores/element'
import { resetImageCrop, startCrop } from '@/apps/slides/stores/imageCrop'
import { allowedImageFileTypes } from '@/apps/slides/utils/constants'
import { handleUploadedMedia } from '@/apps/slides/utils/mediaUploads'

const cropOptions = computed(() => [
	{ value: 'crop', label: __('Crop image'), icon: LucideCrop },
	{
		value: 'reset',
		label: __('Reset crop'),
		icon: LucideRotateCcw,
		disabled: !activeElement.value?.crop,
	},
])

const fileName = computed(() => decodeURIComponent(activeElement.value?.src.split('/').pop() ?? ''))

const handleCropAction = (action) => {
	const el = activeElement.value
	if (action == 'crop') {
		activeElementIds.value = [el.id]
		startCrop(el)
	}
	if (action == 'reset') resetImageCrop(el)
}

const filePicker = useTemplateRef('filePicker')

const openFilePicker = () => filePicker.value.click()

const replaceImage = (e) => {
	const file = e.target.files[0]
	if (file) handleUploadedMedia([file], activeElement.value)
	e.target.value = ''
}
</script>
