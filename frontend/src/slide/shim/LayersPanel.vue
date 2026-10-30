<!-- Layers: every element on the slide, top first, as Builder lists them: click to choose, double-click to name, drag to restack, and an eye and a lock on each. One's own; VENDORED.md. -->
<template>
	<div class="flex flex-col gap-0.5 py-3">
		<p v-if="!layers.length" class="px-1 py-6 text-center text-sm text-ink-gray-5">
			{{ __("Nothing on this slide yet.") }}
		</p>
		<div
			v-for="element in layers"
			:key="element.id"
			draggable="true"
			class="group flex h-8 cursor-pointer items-center gap-2 rounded-4 px-2 text-sm"
			:class="rowClass(element)"
			@click="choose(element, $event)"
			@dblclick="rename(element)"
			@dragstart="dragged = element.id"
			@dragover.prevent="over = element.id"
			@dragleave="over = null"
			@drop.prevent="restack(element.id)"
			@dragend="dragged = over = null"
		>
			<span class="shrink-0 text-ink-gray-6">
				<lucide-type v-if="kindOf(element) === 'text'" class="size-3.5" />
				<lucide-image v-else-if="kindOf(element) === 'image'" class="size-3.5" />
				<lucide-film v-else-if="kindOf(element) === 'video'" class="size-3.5" />
				<lucide-table v-else-if="kindOf(element) === 'table'" class="size-3.5" />
				<lucide-minus v-else-if="kindOf(element) === 'line'" class="size-3.5" />
				<lucide-circle v-else-if="kindOf(element) === 'oval'" class="size-3.5" />
				<lucide-star v-else-if="kindOf(element) === 'star'" class="size-3.5" />
				<lucide-square v-else class="size-3.5" />
			</span>
			<input
				v-if="naming === element.id"
				ref="nameInput"
				v-model="name"
				class="h-6 min-w-0 flex-1 rounded-4 border-0 bg-surface-base px-1 text-sm focus:ring-1 focus:ring-outline-gray-3"
				@keydown.stop.enter="keepName(element)"
				@keydown.stop.esc="naming = null"
				@blur="keepName(element)"
				@click.stop
			/>
			<span v-else class="min-w-0 flex-1 truncate" :class="{ 'text-ink-gray-4': element.hidden }">
				{{ nameOf(element) }}
			</span>
			<button
				type="button"
				:title="element.hidden ? __('Show') : __('Hide')"
				class="flex size-6 items-center justify-center rounded-4 text-ink-gray-6 hover:bg-surface-gray-3"
				:class="element.hidden ? '' : 'invisible group-hover:visible'"
				@click.stop="flip(element, 'hidden')"
			>
				<lucide-eye-off v-if="element.hidden" class="size-3.5" />
				<lucide-eye v-else class="size-3.5" />
			</button>
			<button
				type="button"
				:title="element.locked ? __('Unlock') : __('Lock')"
				class="flex size-6 items-center justify-center rounded-4 text-ink-gray-6 hover:bg-surface-gray-3"
				:class="element.locked ? '' : 'invisible group-hover:visible'"
				@click.stop="flip(element, 'locked')"
			>
				<lucide-lock v-if="element.locked" class="size-3.5" />
				<lucide-lock-open v-else class="size-3.5" />
			</button>
		</div>
	</div>
</template>

<script setup>
import LucideCircle from '~icons/lucide/circle'
import LucideEye from '~icons/lucide/eye'
import LucideEyeOff from '~icons/lucide/eye-off'
import LucideFilm from '~icons/lucide/film'
import LucideImage from '~icons/lucide/image'
import LucideLock from '~icons/lucide/lock'
import LucideLockOpen from '~icons/lucide/lock-open'
import LucideMinus from '~icons/lucide/minus'
import LucideSquare from '~icons/lucide/square'
import LucideStar from '~icons/lucide/star'
import LucideTable from '~icons/lucide/table'
import LucideType from '~icons/lucide/type'
import { computed, nextTick, ref } from 'vue'

import { commandHistory } from '../stores/historyMeta'
import { batchCommand, editElementCommand } from '../stores/commands'
import { activeElementIds, exitTextEditing, focusElementId, setActiveElements } from '../stores/element'
import { currentSlide } from '../stores/slide'
import { __ } from './words.js'

const layers = computed(() =>
	[...(currentSlide.value?.elements || [])].sort((a, b) => (b.zIndex || 1) - (a.zIndex || 1)),
)

const SHAPES = {
	rectangle: __('Rectangle'),
	oval: __('Oval'),
	diamond: __('Diamond'),
	triangle: __('Triangle'),
	pentagon: __('Pentagon'),
	star: __('Star'),
	blockArrow: __('Block Arrow'),
}

const words = (html) => {
	const box = document.createElement('div')
	box.innerHTML = html || ''
	return (box.textContent || '').trim().slice(0, 40)
}

const nameOf = (element) => {
	if (element.name) return element.name
	if (element.type === 'text') return words(element.content) || __('Text')
	if (element.type === 'image') return __('Picture')
	if (element.type === 'video') return __('Video')
	if (element.type === 'table') return __('Table')
	if (element.shapeType === 'line') return element.connector ? __('Connector') : __('Line')
	return words(element.content) || SHAPES[element.shapeType] || __('Shape')
}

const kindOf = (element) => (element.type === 'shape' ? element.shapeType : element.type)

const dragged = ref(null)
const over = ref(null)

const rowClass = (element) => [
	activeElementIds.value.includes(element.id)
		? 'bg-surface-gray-3 text-ink-gray-9'
		: 'text-ink-gray-7 hover:bg-surface-gray-2',
	over.value === element.id && dragged.value !== element.id ? 'ring-1 ring-outline-gray-4' : '',
]

const choose = (element, event) => {
	if (event.shiftKey || event.metaKey || event.ctrlKey) {
		const ids = activeElementIds.value
		activeElementIds.value = ids.includes(element.id) ? ids.filter((id) => id !== element.id) : [...ids, element.id]
		return
	}
	setActiveElements([element.id])
}

const edit = (element, property, newValue) =>
	editElementCommand({
		slideId: currentSlide.value.clientId,
		elementIds: [element.id],
		property,
		oldValue: element[property],
		newValue,
	})

const flip = (element, property) => {
	if (property === 'locked' && !element.locked && focusElementId.value === element.id) exitTextEditing()
	commandHistory.execute(edit(element, property, element[property] ? undefined : true))
}

const naming = ref(null)
const name = ref('')
const nameInput = ref(null)

const rename = async (element) => {
	naming.value = element.id
	name.value = element.name || nameOf(element)
	await nextTick()
	nameInput.value?.[0]?.select()
}

const keepName = (element) => {
	if (naming.value !== element.id) return
	naming.value = null
	const kept = name.value.trim().slice(0, 140) || undefined
	if (kept !== element.name && kept !== nameOf({ ...element, name: undefined }))
		commandHistory.execute(edit(element, 'name', kept))
}

// the dragged element takes the place of the one it is dropped on, and every
// element below moves down one
const restack = (target) => {
	const from = dragged.value
	dragged.value = over.value = null
	if (!from || from === target) return
	const order = layers.value.filter((element) => element.id !== from)
	const at = order.findIndex((element) => element.id === target)
	const moved = layers.value.find((element) => element.id === from)
	const wasAbove = layers.value.indexOf(moved) < layers.value.findIndex((element) => element.id === target)
	order.splice(wasAbove ? at + 1 : at, 0, moved)
	const commands = order
		.map((element, index) => [element, order.length - index])
		.filter(([element, zIndex]) => element.zIndex !== zIndex)
		.map(([element, zIndex]) => edit(element, 'zIndex', zIndex))
	if (!commands.length) return
	commandHistory.execute(
		batchCommand({ slideId: currentSlide.value.clientId, elementIds: [from], commands }),
	)
}
</script>
