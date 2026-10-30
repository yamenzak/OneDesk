<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/LayoutDialog.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Dialog v-model:open="showLayoutDialog" size="4xl" :title="__('Add a Slide')">
		<!-- One: the theme's layouts, or the slide library (shim/SlideLibrary.vue, VENDORED.md) -->
		<TabButtons v-model="shelf" class="mb-4 self-start" :options="[{ label: __('Layouts'), value: 'layouts' }, { label: __('Slide Library'), value: 'library' }]" />
		<SlideLibrary v-if="shelf === 'library'" @insert="insertSlideWithLayout" />
		<div v-else class="no-scrollbar grid max-h-[32rem] grid-cols-3 gap-6 overflow-y-auto">
			<div
				v-for="layout in layouts"
				:key="layout.idx"
				class="aspect-video cursor-pointer overflow-hidden rounded-6 border border-outline-gray-1 hover:border-outline-gray-2"
				:style="getThumbnailCardStyles(layout.thumbnail)"
				@click="insertSlideWithLayout(layout)"
			>
				<SlidePreview
					v-if="layout.thumbnail == ''"
					:slide="layout"
					:scale="LAYOUT_PREVIEW_SCALE"
				/>
			</div>
		</div>
	</Dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Dialog, TabButtons } from 'frappe-ui'
import SlideLibrary from '@/apps/slides/shim/SlideLibrary.vue' // One: VENDORED.md

import SlidePreview from '@/apps/slides/components/SlidePreview.vue'
import { presentationTheme, templateList } from '@/apps/slides/stores/presentation'
import { getThumbnailCardStyles } from '@/apps/slides/utils/helpers'

// card width: 4xl dialog (896) - px-6 (48) - two gap-6 (48), divided by 3
const LAYOUT_PREVIEW_SCALE = 800 / 3 / 960

const emit = defineEmits(['insert'])

const layouts = computed(() => {
	const template = templateList.value?.find((t) => t.name === presentationTheme.value)
	return template?.layouts || []
})

const showLayoutDialog = defineModel('open', { required: true })
const shelf = ref('layouts') // One

const insertSlideWithLayout = (layout) => {
	showLayoutDialog.value = false
	emit('insert', layout)
}
</script>
