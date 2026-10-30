<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/PropertiesPanel.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div data-tour="oneslide-panel" class="flex h-full w-72 flex-col border-l border-outline-elevation-1 bg-surface-elevation-1" @mousedown="keepEditorFocus">
		<!-- One: the panel and Builder's Layers, shim/LayersPanel.vue; VENDORED.md -->
		<div class="shrink-0 px-4 pt-3">
			<TabButtons v-model="panel" :options="panels" class="w-full [&_button]:flex-1" />
		</div>
		<div v-if="panel === 'layers'" class="no-scrollbar flex-1 overflow-y-auto px-2">
			<LayersPanel />
		</div>
		<!-- outside every Section, so locking can never disable the way back out -->
		<template v-else-if="activeElementIds.length">
			<div class="flex shrink-0 items-center justify-between px-4 py-3">
				<span :class="labelClasses">{{ selectionLabel }}</span>
				<button
					type="button"
					:title="isSelectionLocked ? __('Unlock') : __('Lock')"
					:class="lockClasses"
					@click="toggleLock()"
				>
					<lucide-lock v-if="isSelectionLocked" class="size-3.5" />
					<lucide-lock-open v-else class="size-3.5" />
				</button>
			</div>
			<hr class="border-t" />
		</template>
		<div v-if="panel !== 'layers'" class="no-scrollbar flex-1 overflow-y-auto px-4">
			<div v-if="activeElementIds.length">
				<FrameSection />
				<hr class="border-t" />
				<ArrangeSection />
				<template v-if="activeElement?.type === 'table'">
					<hr class="border-t" />
					<TableSection />
					<hr class="border-t" />
					<TableGridSection />
					<hr class="border-t" />
					<TableCellSection />
				</template>
				<template v-if="showFont">
					<hr class="border-t" />
					<FontSection />
					<hr class="border-t" />
					<ParagraphSection />
				</template>
				<template v-if="isShapeSelection && !isEditingShapeText">
					<hr class="border-t" />
					<ShapeStyleSection />
				</template>
				<template v-if="activeElement?.type === 'image'">
					<hr class="border-t" />
					<ImageSection />
				</template>
				<template v-if="activeElement?.type === 'video'">
					<hr class="border-t" />
					<PlaybackSection />
				</template>
				<template v-if="isMediaSelection">
					<hr class="border-t" />
					<BorderSection :key="activeElementIds.join()" />
				</template>
				<template v-if="showShadow">
					<hr class="border-t" />
					<ShadowSection :key="activeElementIds.join()" />
				</template>
				<!-- One: a widget is bare; its look is its element's, as any object's is (shim/WidgetLookSection.vue) -->
				<template v-if="activeElement?.type === 'widget'">
					<hr class="border-t" />
					<WidgetLookSection />
					<hr class="border-t" />
					<BorderSection :key="activeElementIds.join()" />
					<hr class="border-t" />
					<ShadowSection :key="activeElementIds.join()" />
					<hr class="border-t" />
					<WidgetSection />
				</template>
				<template v-else>
					<hr class="border-t" />
					<AppearanceSection />
					<hr class="border-t" />
					<EffectsSection />
					<!-- One: how it comes and goes (shim/MotionSection.vue) -->
					<hr class="border-t" />
					<MotionSection />
				</template>
			</div>
			<div v-else-if="currentSlide">
				<BackgroundSection />
				<!-- One: a screen has one slide, so nothing moves to another -->
				<template v-if="!screen && !masterOf">
					<hr class="border-t" />
					<TransitionSection />
					<hr class="border-t" />
					<SlidePlaybackSection />
					<!-- One: whether this slide shows the master (shim/MasterSection.vue) -->
					<template v-if="master.length">
						<hr class="border-t" />
						<MasterSection />
					</template>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import LucideLock from '~icons/lucide/lock' // One: the island resolves icons only by import, VENDORED.md
import LucideLockOpen from '~icons/lucide/lock-open' // One: the island resolves icons only by import, VENDORED.md
import { computed, provide, ref } from 'vue'
import { TabButtons } from 'frappe-ui'
import WidgetSection from '@/apps/slides/shim/WidgetSection.vue' // One: a widget's settings, VENDORED.md
import WidgetLookSection from '@/apps/slides/shim/WidgetLookSection.vue' // One: a widget's look, VENDORED.md
import { screen } from '@/apps/slides/stores/presentation' // One
import MasterSection from '@/apps/slides/shim/MasterSection.vue' // One: VENDORED.md
import MotionSection from '@/apps/slides/shim/MotionSection.vue' // One: an element comes and goes, VENDORED.md
import { master, masterOf } from '@/apps/slides/shim/master.js' // One

import {
	activeElement,
	activeElementIds,
	activeElements,
	focusElementId,
	isSelectionLocked,
	firstEditableElement,
	toggleLock,
} from '@/apps/slides/stores/element'
import { currentSlide } from '@/apps/slides/stores/slide'

import { labelClasses } from '@/apps/slides/utils/constants'

import FrameSection from './FrameSection.vue'
import ArrangeSection from './ArrangeSection.vue'
import AppearanceSection from './AppearanceSection.vue'
import TableSection from './TableSection.vue'
import TableCellSection from './TableCellSection.vue'
import TableGridSection from './TableGridSection.vue'
import FontSection from './FontSection.vue'
import ParagraphSection from './ParagraphSection.vue'
import ShapeStyleSection from './ShapeStyleSection.vue'
import ImageSection from './ImageSection.vue'
import PlaybackSection from './PlaybackSection.vue'
import BorderSection from './BorderSection.vue'
import ShadowSection from './ShadowSection.vue'
import BackgroundSection from './BackgroundSection.vue'
import TransitionSection from './TransitionSection.vue'
import SlidePlaybackSection from './SlidePlaybackSection.vue'
import EffectsSection from '../shim/EffectsSection.vue'
import LayersPanel from '../shim/LayersPanel.vue'
import { __ } from '../shim/words.js'

const panel = ref('design')
const panels = [
	{ label: __('Design'), value: 'design' },
	{ label: __('Layers'), value: 'layers' },
]

provide('sectionInert', isSelectionLocked)

const isEditingShapeText = computed(
	() => activeElement.value?.type === 'shape' && focusElementId.value === activeElement.value?.id,
)

const isSelectionOf = (...types) =>
	Boolean(firstEditableElement.value) && activeElements.value.every((el) => types.includes(el.type))

const showFont = computed(() => isSelectionOf('text', 'table') || isEditingShapeText.value)
const isShapeSelection = computed(() => isSelectionOf('shape'))
const isMediaSelection = computed(() => isSelectionOf('image', 'video'))
const showShadow = computed(() => isSelectionOf('image', 'video', 'shape'))

const selectionLabel = computed(() => {
	const count = activeElementIds.value.length
	if (count > 1) return __('{0} elements', [count])
	// One: a named element is called by its name, and a kind in the reader's words; VENDORED.md
	if (activeElement.value?.name) return activeElement.value.name
	const kinds = { text: __('Text'), image: __('Image'), video: __('Video'), shape: __('Shape'), table: __('Table') }
	return kinds[activeElement.value?.type] || ''
})

// size-6 keeps the hit area equal to the p-1 icon buttons in ButtonGroup
const lockClasses = computed(() => [
	'flex size-6 cursor-pointer items-center justify-center rounded-4 hover:bg-surface-gray-3',
	isSelectionLocked.value ? 'bg-surface-gray-3 text-ink-gray-7' : 'text-ink-gray-6',
])

const keepEditorFocus = (e) => {
	if (e.target.closest('input, textarea, [draggable="true"]')) return // One: a layer row must be free to drag, VENDORED.md
	e.preventDefault()
}
</script>
