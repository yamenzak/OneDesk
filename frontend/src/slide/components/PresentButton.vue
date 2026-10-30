<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/PresentButton.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div class="flex rounded-4 has-[:focus-visible]:focus-ring">
		<Button
			variant="solid"
			class="rounded-r-none focus-visible:outline-none"
			:iconLeft="Play"
			:label="__('Present', null, 'Play a presentation')"
			@click="emit('start')"
		/>
		<Dropdown :options="options" align="end">
			<Button
				variant="solid"
				icon="lucide-chevron-down"
				:aria-label="__('Presentation options')"
				class="divider rounded-l-none border-l-[0.5px] focus-visible:outline-none data-[state=open]:bg-surface-gray-10"
			/>
		</Dropdown>
	</div>
</template>

<script setup>
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { Play } from 'lucide-vue-next'

import { Button, Dropdown } from 'frappe-ui'

const emit = defineEmits(['start'])

const options = [
	{
		label: __('From the start'),
		icon: 'lucide-skip-back',
		onClick: () => emit('start', { fromStart: true }),
	},
	{
		label: __('On loop'),
		icon: 'lucide-repeat-2',
		onClick: () => emit('start', { loop: true }),
	},
]
</script>

<style scoped>
.divider {
	border-left-color: color-mix(in oklch, currentColor 20%, transparent);
}
</style>
