<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/SlideshowEndScreen.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div class="flex gap-8">
		<Button
			:label="__('Back')"
			size="lg"
			:variant="'outline'"
			class="bg-transparent text-white opacity-70 transition-opacity duration-300 hover:opacity-100"
		>
			<template #prefix>
				<LucideChevronLeft class="size-4 stroke-[1.5]" />
			</template>
		</Button>
		<Button
			:label="__('Replay')"
			size="lg"
			class="opacity-90 transition-opacity duration-200 hover:opacity-100"
			@click.stop="$emit('restartSlideShow')"
		>
			<template #prefix>
				<LucideRotateCcw class="size-4 stroke-[1.5]" />
			</template>
		</Button>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
const emit = defineEmits(['restartSlideShow'])
</script>

<style lang="scss" scoped></style>
